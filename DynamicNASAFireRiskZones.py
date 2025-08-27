#This file imports the models prevoius trained
#and together wit the NASA API it learns form active temperature
#and fire history and further trains the model for better accuracy

import os, io, requests, pandas as pd, geopandas as gpd
from shapely.geometry import Point
from SensoInfo import MAP_KEY_NASA_FIRMS
import numpy as np

MAP_KEY = MAP_KEY_NASA_FIRMS
BBOX = (20.2, 43.6, 29.7, 48.3)
SOURCE = "VIIRS_NOAA21_NRT" # fresh 375m data
DAYS   = 1
BUFFER_M = 600

world_shape = gpd.read_file("Assets_AI/Country_shape.shp")

if world_shape.crs is None:
    world_shape = world_shape.set_crs("EPSG:4326")

if world_shape.crs.to_epsg() != 4326:
    world_shape = world_shape.to_crs(4326)

romania_shape = world_shape[world_shape['SOVEREIGNT'] == 'Romania']
rom_polygon   = romania_shape.geometry.unary_union

def fetch_firms_csv(map_key: str) -> pd.DataFrame:
    url = (
        "https://firms.modaps.eosdis.nasa.gov/api/area/csv/"
        f"{map_key}/{SOURCE}/{BBOX[0]},{BBOX[1]},{BBOX[2]},{BBOX[3]}/{DAYS}"
    )
    csv = requests.get(url, timeout=30)
    csv.raise_for_status()
    fires_df = pd.read_csv(io.StringIO(csv.text))
    if fires_df.empty:
        return fires_df
    fires_df.rename(columns={'lat':'latitude','lon':'longitude'}, inplace=True)
    return fires_df

def get_fires_gdf(map_key: str) -> gpd.GeoDataFrame:
    fires_df = fetch_firms_csv(map_key)
    if fires_df.empty:
        return gpd.GeoDataFrame(fires_df, geometry=[], crs="EPSG:4326")
    fires_gdf = gpd.GeoDataFrame(
        fires_df,
        geometry=[Point(xy) for xy in zip(fires_df.longitude, fires_df.latitude)],
        crs="EPSG:4326"
    )
    fires_gdf = fires_gdf[fires_gdf.intersects(rom_polygon)]
    return fires_gdf

#====MODEL LOADING====
import joblib
vegetation_clf = joblib.load("models/vegetation_rf.joblib")
fire_model = joblib.load("models/fire_rf_latest.joblib")

HIGH = 4
#grid_gdf=grid_gdf.to_crs(3857)
#high_gdf = grid_gdf[grid_gdf["Predicted_Fire_Risk"] >= HIGH]


def predict_grid(grid_gdf_4326: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    assert {'Latitude','Longitude'}.issubset(grid_gdf_4326.columns), "grid_gdf must have Latitude, Longitude"
    veg_pred = vegetation_clf.predict(grid_gdf_4326[["Latitude","Longitude"]])
    X = np.c_[grid_gdf_4326["Latitude"].values,
              grid_gdf_4326["Longitude"].values,
              veg_pred]
    risk_class = fire_model.predict(X)
    out = grid_gdf_4326.copy()
    out["Predicted_Vegetation"] = veg_pred.astype(int)
    out["Predicted_Fire_Risk"] = risk_class.astype(int)
    return out

#=====Accuracy based on how many generated points intersect the actual real fire zone=====

def evaluate_vs_firms(preds_4326: gpd.GeoDataFrame, fires_4326: gpd.GeoDataFrame):
    if fires_4326.empty:
        return dict(tp=0, fp=0, fn=0, precision=1.0 if (preds_4326[preds_4326["Predicted_Fire_Risk"]>=HIGH].empty) else 0.0, recall=1.0)

    # Work in meters
    preds_3857 = preds_4326.to_crs(3857)
    fires_3857 = fires_4326.to_crs(3857)

    # Buffer fires and union
    buf_union = gpd.GeoSeries(fires_3857.buffer(BUFFER_M), crs=3857).union_all()

    # TP/FP fire-risk points
    high = preds_3857[preds_3857["Predicted_Fire_Risk"] >= HIGH]
    intersects = high.geometry.intersects(buf_union)
    tp = int(intersects.sum())
    fp = int((~intersects).sum())

    # FN: low/med risk but inside buffer
    lowmed = preds_3857[preds_3857["Predicted_Fire_Risk"] < HIGH]
    fn = int(lowmed.geometry.intersects(buf_union).sum())

    precision = tp / max(tp+fp, 1)
    recall    = tp / max(tp+fn, 1)
    print(f"Precision={precision:.2f}, Recall={recall:.2f}  (window={DAYS} day, buffer=600 m)")
    return dict(tp=tp, fp=fp, fn=fn, precision=precision, recall=recall)

def downsample_by_risk(gdf: gpd.GeoDataFrame, ratio=0.4, risk_col='Predicted_Fire_Risk',
                       weights={1:1, 2:2, 3:3, 4:4}, seed=42) -> gpd.GeoDataFrame:
    if gdf.empty:
        return gdf
    N = len(gdf)
    target = max(1, int(np.ceil(ratio * N)))

    parts = []
    counts = gdf[risk_col].value_counts().to_dict()
    total_weighted = sum(counts.get(r, 0) * weights.get(r, 1) for r in (1,2,3,4)) or 1

    quotas = {}
    assigned = 0
    for r in (4,3,2,1):
        n_r = counts.get(r, 0)
        if n_r == 0:
            quotas[r] = 0
            continue
        q = int(round(target * (n_r * weights.get(r,1)) / total_weighted))
        q = min(q, n_r)
        quotas[r] = q
        assigned += q

    # fix rounding to hit target: add/remove from higher risk first
    while assigned < target:
        for r in (4,3,2,1):
            n_r = counts.get(r, 0)
            if quotas.get(r,0) < n_r:
                quotas[r] += 1
                assigned += 1
                if assigned == target: break
    while assigned > target:
        for r in (1,2,3,4):  # trim from low risk first
            if quotas.get(r,0) > 0:
                quotas[r] -= 1
                assigned -= 1
                if assigned == target: break

    rng = np.random.RandomState(seed)
    for r in (4,3,2,1):
        q = quotas.get(r, 0)
        if q <= 0:
            continue
        grp = gdf[gdf[risk_col] == r]
        if q == len(grp):
            parts.append(grp)
        else:
            parts.append(grp.sample(n=q, replace=False, random_state=rng))

    out = pd.concat(parts).sample(frac=1.0, random_state=seed)
    return out

import json
def gdf_to_featurecollection(gdf: gpd.GeoDataFrame):
    if gdf.empty:
        return {"type":"FeatureCollection","features":[]}
    return json.loads(gdf.to_json())
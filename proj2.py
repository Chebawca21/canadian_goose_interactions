import pandas as pd
import geopandas as gpd
from shapely import Point, LineString

def load_goose_csv(filename):
    df = pd.read_csv(filename)

    geometry = []
    for _, row in df.iterrows():
        geometry.append(Point(row['location-long'], row['location-lat']))
    
    df = df.drop(['location-long', 'location-lat', 'event-id', 'visible', 'sensor-type', 'tag-local-identifier', 'individual-taxon-canonical-name', 'study-name'], axis='columns')
    df = gpd.GeoDataFrame(df, geometry=geometry)
    df.crs = "Epsg:4326"
    df = df.to_crs(epsg=4326)
    return df

def group_by_goose(gdf):
    linestrings = {}
    animals = gdf['individual-local-identifier'].unique()
    for animal in animals:
        animal_gdf = gdf[gdf['individual-local-identifier'] == animal]
        animal_gdf = animal_gdf.sort_values('timestamp')
        linestrings[animal] = LineString(animal_gdf['geometry'].to_list())
    
    data = {}
    data['animal_tag'] = []
    data['geometry'] = []
    for key, value in linestrings.items():
        data['animal_tag'].append(key)
        data['geometry'].append(value)
    
    new_gdf = gpd.GeoDataFrame(data)
    new_gdf.crs = "Epsg:4326"
    new_gdf = new_gdf.to_crs(epsg=4326)
    return new_gdf

def save_intersections_to_file(gdf, foldername):
    for _, row1 in gdf.iterrows():
        intersections = {}
        intersections['animal_tag1'] = []
        intersections['animal_tag2'] = []
        intersections['geometry'] = []

        for _, row2 in gdf.iterrows():
            if row1.animal_tag != row2.animal_tag:
                intersections['animal_tag1'].append(row1.animal_tag)
                intersections['animal_tag2'].append(row2.animal_tag)
                intersections['geometry'].append(row1.geometry.intersection(row2.geometry))

        intersections_df = pd.DataFrame(intersections)
        intersections_df.to_csv(f"{foldername}/{row1.animal_tag}_intersections.csv")
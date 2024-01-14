import pandas as pd
import itertools
import numpy as np
from datetime import datetime
import rasterio
from pyproj import Transformer

def load_goose_csv(filename):
    df = pd.read_csv(filename)
    df = df.drop(['event-id', 'visible', 'sensor-type', 'tag-local-identifier', 'individual-taxon-canonical-name', 'study-name'], axis='columns')
    return df

def round_lat_long(df):
    df['location-long'] = df['location-long'].apply(lambda x: np.round(x * 2, 4) / 2)
    df['location-lat'] = df['location-lat'].apply(lambda x: np.round(x * 2, 4) / 2)
    return df

def get_intersections(df):
    animals = df['individual-local-identifier'].unique()
    animal_pairs = list(itertools.combinations(animals, 2))

    bird_intersections = pd.DataFrame()
    for animal1, animal2 in animal_pairs:
        bird1 = df[df['individual-local-identifier'] == animal1]
        bird2 = df[df['individual-local-identifier'] == animal2]
        intersctions = bird1.merge(bird2, on=['location-long', 'location-lat'])
        bird_intersections = pd.concat([bird_intersections, intersctions])
    return bird_intersections

def delete_false_intersections(bird_intersections, time_window=1200):
    bird_intersections['timestamp_x'] = bird_intersections['timestamp_x'].apply(lambda x: datetime.strptime(x, '%Y-%m-%d %H:%M:%S.%f'))
    bird_intersections['timestamp_y'] = bird_intersections['timestamp_y'].apply(lambda x: datetime.strptime(x, '%Y-%m-%d %H:%M:%S.%f'))
    bird_intersections['time_diff'] = bird_intersections['timestamp_x'] - bird_intersections['timestamp_y']
    bird_intersections['time_diff'] = bird_intersections['time_diff'].apply(lambda x: abs(x.total_seconds()))
    bird_intersections = bird_intersections.drop(['timestamp_x', 'timestamp_y'], axis='columns')

    bird_intersections = bird_intersections[bird_intersections['time_diff'] <= time_window]
    return bird_intersections

def get_val_from_tif(dat, x, y):
    values = list(rasterio.sample.sample_gen(dat, [(x, y)]))
    return values[0][0]

def add_terrain_info(bird_interactions, filename):
    dat = rasterio.open('land_cover_2020_30m_tif/NA_NALCMS_landcover_2020_30m/data/NA_NALCMS_landcover_2020_30m.tif')
    transformer = Transformer.from_crs("epsg:4326", dat.crs)

    terrain = []
    for _, row in bird_interactions.iterrows():
        x, y = transformer.transform(row['location-lat'], row['location-long'])
        terrain.append(get_val_from_tif(dat, x, y))


goose_file = "North-East_American_Canada_goose_migration.csv"
tif_file = "land_cover_2020_30m_tif/NA_NALCMS_landcover_2020_30m/data/NA_NALCMS_landcover_2020_30m.tif"

df = load_goose_csv(goose_file)
df_rounded = round_lat_long(df)
bird_intersections = get_intersections(df_rounded)
bird_interactions = delete_false_intersections(bird_intersections)
bird_interactions = add_terrain_info(bird_interactions, tif_file)
bird_interactions.to_csv("bird_interactions", index=False)
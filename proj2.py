import pandas as pd
import itertools
import numpy as np
from datetime import datetime
import rasterio
from pyproj import Transformer

terrain_dict = {
    0: 'Sea or ocean',
    1: 'Temperate or sub-polar needleleaf forest',
    2: 'Sub-polar taiga needleleaf forest',
    3: 'Tropical or sub-tropical broadleaf evergreen forest',
    4: 'Tropical or sub-tropical broadleaf deciduous forest',
    5: 'Temperate or sub-polar broadleaf deciduous forest',
    6: 'Mixed Forest',
    7: 'Tropical or sub-tropical shrubland',
    8: 'Temperate or sub-polar shrubland',
    9: 'Tropical or sub-tropical grassland',
    10: 'Temperate or sub-polar grassland',
    11: 'Sub-polar or polar shrubland-lichen-moss',
    12: 'Sub-polar or polar grassland-lichen-moss',
    13: 'Sub-polar or polar barren-lichen-moss',
    14: 'Wetland',
    15: 'Cropland',
    16: 'Barren lands',
    17: 'Urban',
    18: 'Water',
    19: 'Snow and Ice'
}

goose_file = "North-East_American_Canada_goose_migration.csv"
tif_file = "land_cover_2020_30m_tif/NA_NALCMS_landcover_2020_30m/data/NA_NALCMS_landcover_2020_30m.tif"

def load_goose_csv(filename=goose_file):
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

def add_terrain_info(dataframe, filename=tif_file):
    dat = rasterio.open(filename)
    transformer = Transformer.from_crs("epsg:4326", dat.crs)

    terrain = []
    for _, row in dataframe.iterrows():
        x, y = transformer.transform(row['location-lat'], row['location-long'])
        terrain.append(get_val_from_tif(dat, x, y))
    dataframe['terrain'] = terrain
    dataframe['terrain_str'] = dataframe['terrain'].apply(lambda x: terrain_dict[x])


if __name__ == "__main__":
    df = load_goose_csv(goose_file)
    df_rounded = round_lat_long(df)
    bird_intersections = get_intersections(df_rounded)
    bird_interactions = delete_false_intersections(bird_intersections)
    bird_interactions = add_terrain_info(bird_interactions, tif_file)
    bird_interactions.to_csv("bird_interactions", index=False)
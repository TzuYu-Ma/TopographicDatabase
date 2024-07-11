import psycopg2
from flask import Flask
import os


# create the Flask app
app = Flask(__name__) 

# create the index route
@app.route('/') 
def index(): 
    return "The API is working!"

# create a general DB to GeoJSON function based on a SQL query
def database_to_geojson_by_query(sql_query):
    # create connection to the DB
    conn = psycopg2.connect(
        host=os.environ.get("DB_HOST"),
        database=os.environ.get("DB_NAME"),
        user=os.environ.get("DB_USER"),
        password=os.environ.get("DB_PASS"),
        port=os.environ.get("DB_PORT"),
    )
    # retrieve the data
    with conn.cursor() as cur:
        cur.execute(sql_query)
        # fetchall() will return a list of tuples
        data = cur.fetchall()
    # close the connection
    conn.close()

    # Convert query result to GeoJSON format
    features = []
    for row in data:
        # each row is a GeoJSON feature
        geometry_wkb = row[4]  # GeoJSON geometry is in the last column
        feature = {
            "type": "Feature",
            "properties": {
                "objectid": row[0],
                "pointid": row[1],
                "cumulative_gdd": row[2]
            },
            "geometry": geometry_wkb
        }
        features.append(feature)

    # Creating GeoJSON FeatureCollection
    geojson_data = {
        "type": "FeatureCollection",
        "features": features
    }

    return geojson_data



# create a general DB to GeoJSON function based on a table name
def database_to_geojson_by_table_name(table_name):
        # create connection to the DB
    conn = psycopg2.connect(
        host=os.environ.get("DB_HOST"),
        database=os.environ.get("DB_NAME"),
        user=os.environ.get("DB_USER"),
        password=os.environ.get("DB_PASS"),
        port=os.environ.get("DB_PORT"),
    )
    # retrieve the data
    with conn.cursor() as cur:
        query =f"""
        SELECT JSON_BUILD_OBJECT(
            'type', 'FeatureCollection',
            'features', JSON_AGG(
                ST_AsGeoJson({table_name}.*)::json
            )
        )
        FROM {table_name};
        """
        
        cur.execute(query)
        
        data = cur.fetchall()
    # close the connection
    conn.close()
    
    # Returning the data
    return data [0][0]



# create the data route
# AGDD
@app.route('/agdd/minnesota', methods=['GET'])
def get_agdd_minnesota():
    # call our general function
    agdd_minnesota = database_to_geojson_by_table_name("samp_agdd_idw")
    return agdd_minnesota



@app.route('/agdd/<countyname>', methods=['GET'])
def get_agdd_county(countyname):
    sql_query = f"""
        SELECT agdd.*,
        ST_AsGeoJSON(agdd.shape)::json AS geometry
        FROM samp_agdd_idw AS agdd
        JOIN mn_county_1984 AS county ON ST_Contains(county.shape, agdd.shape)
        WHERE county.COUNTYNAME = '{countyname}';
    """

    agdd_county = database_to_geojson_by_query(sql_query)
    return agdd_county

# Soil 
@app.route('/soil_moisture/<date>', methods=['GET'])
def get_soil_moisture_geojson(date):
    # call our general function with the provided date
    sm = database_to_geojson_by_table_name("samp_soil_moisture_" + date)
    return sm


@app.route('/soil_moisture/<date>/<countyname>', methods=['GET'])
def get_soil_moisture_county(date, countyname):
    # Construct the table name based on the provided date
    sm_county = "samp_soil_moisture_" + date

    # Construct the SQL query to retrieve soil moisture data for the specified county
    sql_query = f"""
        SELECT {sm_county}.*,
        ST_AsGeoJSON({sm_county}.shape)::json AS geometry
        FROM {sm_county} 
        JOIN mn_county_1984 AS county ON ST_Contains(county.shape, {sm_county}.shape)
        WHERE county.COUNTYNAME = '{countyname}';
    """

    # Execute the SQL query and return the result as GeoJSON
    sm_county_geojson = database_to_geojson_by_query(sql_query)
    return sm_county_geojson


# ET

@app.route('/et/<date>', methods=['GET'])
def get_et_geojson(date):
    # call our general function with the provided date
    et = database_to_geojson_by_table_name("samp_et_" + date)
    return et


@app.route('/et/<date>/<countyname>', methods=['GET'])
def get_et_county(date, countyname):
    # Construct the table name based on the provided date
    et_county = "samp_et_" + date

    # Construct the SQL query to retrieve soil moisture data for the specified county
    sql_query = f"""
        SELECT {et_county}.*,
        ST_AsGeoJSON({et_county}.shape)::json AS geometry
        FROM {et_county} 
        JOIN mn_county_1984 AS county ON ST_Contains(county.shape, {et_county}.shape)
        WHERE county.COUNTYNAME = '{countyname}';
    """

    # Execute the SQL query and return the result as GeoJSON
    et_county_geojson = database_to_geojson_by_query(sql_query)
    return et_county_geojson

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
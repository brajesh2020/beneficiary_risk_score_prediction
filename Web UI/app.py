from flask import Flask, render_template, request, redirect, url_for
from sqlalchemy import create_engine
import pandas as pd
from fuzzywuzzy import process
from flask_caching import Cache

app = Flask(__name__)

# Path to SQLite database
db_path = 'D://reva project 2024//SQL5_FOR_MEDICARE_ANALYSIS.db'

# Setup SQLAlchemy connection with pooling
engine = create_engine(f'sqlite:///{db_path}', pool_size=5, max_overflow=10)

# Flask-Caching configuration
cache = Cache(app, config={'CACHE_TYPE': 'simple'})  # Simple in-memory cache


# Query caching for frequently accessed data
@cache.cached(timeout=300)  # Cache for 5 minutes
def get_top_states():
    query = '''
    SELECT distinct Rndrng_Prvdr_State_NAME, Rndrng_Prvdr_State_Abrvtn, Rndrng_Prvdr_City_New,Rndrng_Prvdr_Type,
    ROUND(SUM(Med_Tot_Benes) / 1000000, 2) AS Patients_Served_in_Millions,
    ROUND((Tot_Mdcr_Stdzd_Amt / Tot_Srvcs) / 1000000, 2) AS Avg_Mdcr_Stdzd_Amt_per_service,
    ROUND(AVG(Bene_Avg_Risk_Scre), 2) AS Avg_Risk_Scre    
    FROM raw_data_transformed
    GROUP BY Rndrng_Prvdr_State_NAME, Rndrng_Prvdr_State_Abrvtn, Rndrng_Prvdr_City_New,Rndrng_Prvdr_Type
    ORDER BY Patients_Served_in_Millions DESC
    LIMIT 50    '''
    conn = engine.connect()
    result = pd.read_sql_query(query, conn)
    conn.close()
    print('get_top_states',result.columns)
    return result

@cache.cached(timeout=300)
def get_top_cities():
    query = '''
    SELECT distinct Rndrng_Prvdr_City_New,  
    ROUND(SUM(Med_Tot_Benes) / 1000000, 2) AS Patients_Served_in_Millions,
    ROUND((Tot_Mdcr_Stdzd_Amt / Tot_Srvcs) / 1000000, 2) AS Avg_Mdcr_Stdzd_Amt_per_service,
    ROUND(AVG(Bene_Avg_Risk_Scre), 2) AS Avg_Risk_Scre
    FROM raw_data_transformed
    GROUP BY Rndrng_Prvdr_City_New
    ORDER BY Patients_Served_in_Millions DESC
    LIMIT 50    '''
    conn = engine.connect()
    result = pd.read_sql_query(query, conn)
    conn.close()
    print('get_top_cities',result.columns)
    return result

@cache.cached(timeout=300)
def get_top_provider_type():
    query = '''
    SELECT distinct Rndrng_Prvdr_Type,  
    ROUND(SUM(Med_Tot_Benes) / 1000000, 2) AS Patients_Served_in_Millions,
    ROUND((Tot_Mdcr_Stdzd_Amt / Tot_Srvcs) / 1000000, 2) AS Avg_Mdcr_Stdzd_Amt_per_service,
    ROUND(AVG(Bene_Avg_Risk_Scre), 2) AS Avg_Risk_Scre
    FROM raw_data_transformed
    GROUP BY Rndrng_Prvdr_Type
    ORDER BY Patients_Served_in_Millions , Avg_Risk_Scre DESC
    LIMIT 50    '''
    conn = engine.connect()
    result = pd.read_sql_query(query, conn)
    conn.close()
    print('get_top_provider_type',result.columns)
    return result


def get_top_providers(zip_code):
    query = '''
    SELECT distinct a.Rndrng_Prvdr_First_Name, a.Rndrng_Prvdr_Last_Org_Name,a. Rndrng_Prvdr_St1, a.Rndrng_Prvdr_St2,
           a.Rndrng_Prvdr_City_New, a.Rndrng_Prvdr_Zip5,a. Rndrng_Prvdr_State_NAME, b.latitude2,b. longitude2
           ,      ROUND(SUM(Med_Tot_Benes) / 1000000, 2) AS Patients_Served_in_Millions,
    ROUND((Tot_Mdcr_Stdzd_Amt / Tot_Srvcs) / 1000000, 2) AS Avg_Mdcr_Stdzd_Amt_per_service,
    ROUND(AVG(Bene_Avg_Risk_Scre), 2) AS Avg_Risk_Scre
    FROM raw_data_transformed a
    left join normalized_addresses b on a.Rndrng_Prvdr_Zip5=b.Rndrng_Prvdr_Zip5
    WHERE a.Rndrng_Prvdr_Zip5 = ?
    AND b.latitude2 IS NOT NULL
    LIMIT 20'''
    conn = engine.connect()
    result = pd.read_sql_query(query, conn, params=(zip_code,))
    conn.close()
    print('get_top_providers', result.columns)
    return result

def get_zip_codes_by_state(state):
    query = '''
    SELECT distinct Rndrng_Prvdr_Zip5
    , SUM(Med_Tot_Benes) AS Total_Benes
    ,ROUND((Tot_Mdcr_Stdzd_Amt / Tot_Srvcs) / 1000000, 2) AS Avg_Mdcr_Stdzd_Amt_per_service
    ,ROUND(SUM(Med_Tot_Benes) / 1000000, 2) AS Patients_Served_in_Millions
    ,ROUND((Tot_Mdcr_Stdzd_Amt / Tot_Srvcs) / 1000000, 2) AS Avg_Mdcr_Stdzd_Amt_per_service
    ,ROUND(AVG(Bene_Avg_Risk_Scre), 2) AS Avg_Risk_Scre    
    FROM raw_data_transformed
    WHERE LOWER(Rndrng_Prvdr_State_NAME) = ? OR LOWER(Rndrng_Prvdr_State_Abrvtn) = ? OR LOWER(Rndrng_Prvdr_City_new) = ?
    GROUP BY Rndrng_Prvdr_Zip5
    ORDER BY Total_Benes DESC
    LIMIT 10
    '''
    conn = engine.connect()
    result = pd.read_sql_query(query, conn, params=(state.lower(), state.lower(), state.lower()))
    conn.close()
    print('get_zip_codes_by_state',result.columns)
    return result

# Fuzzy matching for location search
def find_best_matching_state(location):
    states = get_top_states()
    states_list = states['Rndrng_Prvdr_State_NAME'].str.lower().tolist()
    best_match = process.extractOne(location.lower(), states_list)
    if best_match and best_match[1] >= 80:  # Confidence threshold
        print('find_best_matching_state',best_match[0])
        return best_match[0]
    return None

def find_best_matching_city(location):
    cities = get_top_cities()
    if 'Rndrng_Prvdr_City_New' not in cities.columns:
        print("Column 'Rndrng_Prvdr_City_New' not found")
        return None

    cities_list = cities['Rndrng_Prvdr_City_New'].str.lower().tolist()
    print(cities_list)
    best_match = process.extractOne(location.lower(), cities_list)
    if best_match and best_match[1] >= 80:
        print('find_best_matching_city', best_match[0])
        return best_match[0]
    return None


def find_best_matching_provider_type(location):
    provider_types = get_top_provider_type()
    provider_type_list = provider_types['Rndrng_Prvdr_Type'].str.lower().tolist()
    best_match = process.extractOne(location.lower(), provider_type_list)
    if best_match and best_match[1] >= 80:
        print('find_best_matching_provider_type',best_match[0])
        return best_match[0]
    return None

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        location = request.form.get('location').lower()
        best_match_state = find_best_matching_state(location)
        best_match_city = find_best_matching_city(location)
        best_match_provider_type = find_best_matching_provider_type(location)

        if best_match_state:
            return redirect(url_for('zip_codes', location=best_match_state.lower()))
        elif best_match_city:
            return redirect(url_for('zip_codes', location=best_match_city.lower()))
        elif best_match_provider_type:
            return redirect(url_for('zip_codes', location=best_match_provider_type.lower()))
        else:
            return render_template('index.html',
                                   error="State or City not found. Please check the spelling or try another name.")
    top_states = get_top_states()
    top_cities = get_top_cities()
    top_provider_type = get_top_provider_type()
    return render_template('index.html', top_states=top_states, top_cities=top_cities,
                           top_provider_type=top_provider_type,enumerate=enumerate)

@app.route('/zip_codes/<location>', methods=['GET'])
def zip_codes(location):
    zip_codes = get_zip_codes_by_state(location)
    return render_template('zip_codes.html', location=location, zip_codes=zip_codes)

@app.route('/providers/<zip_code>', methods=['GET'])
def providers(zip_code):
    top_providers = get_top_providers(zip_code)
    if not top_providers.empty:
        Rndrng_Prvdr_City_New = top_providers.iloc[0]['Rndrng_Prvdr_City_New']
        Rndrng_Prvdr_State_NAME = top_providers.iloc[0]['Rndrng_Prvdr_State_NAME']
    else:
        Rndrng_Prvdr_City = None
        Rndrng_Prvdr_State_NAME = None
    return render_template('providers.html', zip_code=zip_code, top_providers=top_providers,
                           Rndrng_Prvdr_City_New=Rndrng_Prvdr_City_New, Rndrng_Prvdr_State_NAME=Rndrng_Prvdr_State_NAME)

if __name__ == "__main__":
    app.run(debug=True)

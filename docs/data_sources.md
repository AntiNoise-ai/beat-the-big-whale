# Data Sources and Access Notes

## Confirmed working without registration

### 1. TfL station metadata API
Purpose:
- station names
- lat/lon
- zone
- served lines

Endpoint:
- https://api.tfl.gov.uk/StopPoint/Mode/tube

Notes:
- reachable without an API key
- returns station entries plus entrances/platforms/access areas
- Phase 1 extraction filters to `NaptanMetroStation`

### 2. TfL line metadata API
Endpoint:
- https://api.tfl.gov.uk/Line/Mode/tube

### 3. TfL annual station counts
Purpose:
- footfall proxy / entries-exits proxy

Direct file:
- https://crowding.data.tfl.gov.uk/Annual%20Station%20Counts/2023/AC2023_AnnualisedEntryExit.xlsx

Notes:
- reachable without registration
- suitable for footfall feature engineering

### 4. Geofabrik Greater London extract
Purpose:
- OSM-based POI counts around stations

Direct files:
- https://download.geofabrik.de/europe/united-kingdom/england/greater-london-latest-free.shp.zip
- https://download.geofabrik.de/europe/united-kingdom/england/greater-london-latest.osm.pbf

Notes:
- reachable without registration
- shapefile zip is easier to start with

## Accessible, but account/API key may help later

### 5. NOMIS API
Docs:
- https://www.nomisweb.co.uk/api/v01/help
- https://www.nomisweb.co.uk/api/v01/dataset/

Candidate datasets identified:
- `NM_57_1` — jobs density
- `NM_100_1` — annual population survey - workplace analysis
- `NM_155_1` — workplace population density
- `NM_156_1` — distance travelled to work (workplace population)
- `NM_172_1` / `NM_189_1` — Business Register and Employment Survey open access
- `NM_31_1` — population estimates by five year age band
- `NM_561_1` / `NM_945_1` — occupation tables / workday population occupation
- `NM_568_1` — method of travel to work

Notes:
- API works anonymously
- anonymous access is limited to 25,000 cells
- for larger pulls, create an account and use a Nomis UID/signature
- local scripts should read `NOMIS_UID` from the environment and must not commit credentials or keys

If needed later, registration page is:
- https://www.nomisweb.co.uk/

### 6. TfL open data docs
Docs:
- https://tfl.gov.uk/info-for/open-data-users/
- https://tfl.gov.uk/info-for/open-data-users/api-documentation

Notes:
- current station metadata calls worked without credentials
- an app key may still be useful for reliability / rate limits later

## Current recommendation

Immediate Phase 1 can proceed with no registration using:
- TfL station metadata API
- TfL annual station counts file
- Geofabrik London extract

Possible first registration later:
- NOMIS account for larger demographic/workplace pulls

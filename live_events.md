## Live Events

Live events are events reported by users in real time, such as Waze events. Other types of live events can exist, such as our own events (possible future feature) or SCDB mobile cameras provided externally.

### Waze Events

We exclusively use the OpenWebNinja API for Waze events.

Documentation:
[Link](https://www.openwebninja.com/api/waze/docs?_gl=1*17jwh8u*_ga*MTM1NzUyNDU0My4xNzcyMTI2Mjcx*_ga_6N3TJCS0C6*czE3NzY1ODI5MjUkbzYkZzEkdDE3NzY1ODMwOTQkajYwJGwwJGgw)

We use the `/alerts-and-jams` endpoint as that is the only thing relevant to what we want.

This endpoint returns alert objects and jam objects.

#### Alerts and Types of Alerts

Each alert has a `type` field and a `subtype` field - the subtype can be null.

Note that this list is experimentally derived (there is no official list in the docs). Certain types or subtypes may be missing.

- HAZARD
  - HAZARD_ON_ROAD_POTHOLE
  - HAZARD_ON_ROAD_CONSTRUCTION
  - HAZARD_ON_ROAD_OBJECT
  - HAZARD_ON_SHOULDER_CAR_STOPPED
- POLICE
  - POLICE_WITH_MOBILE_CAMERA
  - POLICE_HIDING
- ROAD_CLOSED
- ACCIDENT

Example object:

```
{
  "alert_id": "656751357",
  "type": "POLICE",
  "subtype": "POLICE_HIDING",
  "reported_by": null,
  "description": null,
  "image": null,
  "publish_datetime_utc": "2026-04-19T07:51:41.000Z",
  "country": "BU",
  "city": "София",
  "street": "ул. Суходолска",
  "latitude": 42.699278,
  "longitude": 23.276644,
  "num_thumbs_up": 0,
  "alert_reliability": 5,
  "alert_confidence": 0,
  "near_by": null,
  "comments": [],
  "num_comments": 0
}
```

| Column               | Type     | Description                                                                              |
|----------------------|----------|------------------------------------------------------------------------------------------|
| alert_id             | string   |                                                                                          |
| type                 | enum     |                                                                                          |
| subtype              | enum     |                                                                                          |
| reported_by          | ?        |                                                                                          |
| description          | ?        |                                                                                          |
| image                | ?        |                                                                                          |
| publish_datetime_utc | datetime |                                                                                          |
| country              | enum     | Non-standard country code, Waze-specific. Eg. "BU" for Bulgaria, "EZ" for Czech Republic |
| city                 | string   |                                                                                          |
| street               | string   |                                                                                          |
| latitude             | double   |                                                                                          |
| longitude            | double   |                                                                                          |
| num_thumbs_up        | int      |                                                                                          |
| alert_reliability    | int      |                                                                                          |
| alert_confidence     | int      |                                                                                          |
| near_by              | ?        |                                                                                          |
| comments             | array    |                                                                                          |
| num_comments         | int      |                                                                                          |

### Our Events

We have our own live event schema. This is because we don't want to expose that we use OpenWebNinja API, we don't need everything from it, plus we want to use other data sources in the future.

We return the response as GeoJSON. The schema refers to the `properties` field on the object.

Our schema:

```
{
  id: string // unique to our system
  type: string
  published_at: int // timestamp
  country: string // 2-letter country code
  reverse_geocode: MapboxReverseGeocodeData
  osm_road: OverpassEnrichmentData
}
```

Types:
- hazard_pothole
- hazard_construction
- hazard_object_on_road
- hazard_vehicle_on_road
- hazard_accident
- hazard_other
- police
- police_mobile_camera
- road_closure

The final `/dangers` response comes from our API as:

```
{
  "points": [
    // Fixed points (integrated as tilesets)
    // Speed cams, red light cams
  ],
  "points_live": [
    // Example object:
    {
      "type": "Feature",
      "geometry": {
        "type": "Point",
        "coordinates": [
          26.50926962912519,
          42.47929705832257
        ]
      },
      "properties": {
        "id": "84793274982",
        "type": "police",
        "published_at": 1776590271114,
        "country": "BG",
        "reverse_geocode": {
          // same object structure as in the fixed dangers
        },
        "osm_road": {
         // same object structure as in the fixed dangers
        }
      }
    }
  ],
  "polylines": [
    // Section control segments
  ],
  "polygons": [
    // LEZs, LTZs, ZTLs etc
  ]
}
```
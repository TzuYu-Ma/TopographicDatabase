# Topographic Database - Taiwan

## Overview
This project uses Google Cloud products (Virtual Machine, SQL, Cloud Run) and a Flask APP to organize topographic data in Taiwan. The database includes 1:25,000 scale datasets and provides data in GeoJSON format.

## WebMap Link

Access the WebMap using the following URL:

- **[WebMap](https://experience.arcgis.com/experience/b1f22c6dfc674fac91b47700b90408ce/)**

## Data URLs for GeoJSON

**[Root URL return](/images/webpage.jpg)**

- **Root URL:**
  ```plaintext
  https://cloudrun-zjoivcfvsa-uc.a.run.app
  ```

### Retrieve Data by Grid Number

You can retrieve data by using the grid number:

- **URL Format:** 
```plaintext
https://cloudrun-zjoivcfvsa-uc.a.run.app/{grid_number}
```

#### 25k Grid Numbers

| Grid Number | Grid Number | Grid Number | Grid Number |
|-------------|-------------|-------------|-------------|
| 94171SE     | 96183NW     | 96211NE     | 96222NW     |
| 94171SW     | 96183SW     | 96211NW     | 96222SE     |
| 96172SE     | 96184NE     | 96211SE     | 96222SW     |
| 96181NW     | 96184NW     | 96211SW     | 96223NE     |
| 96182NE     | 96184SE     | 96212NE     | 96223NW     |
| ...         | ...         | ...         | ...         |

(Note: 25k grid numbers have a lot, recommend using WebMap to select the desired grid.)

#### 50k Grid Numbers

| Grid Number | Grid Number | Grid Number | Grid Number |
|-------------|-------------|-------------|-------------|
| 94181       | 95174       | 97194       | 96181       |
| 94182       | 95181       | 97203       | 96182       |
| 94183       | 95182       | 97204       | 96183       |
| 94184       | 95183       | 97211       | 96184       |
| 94191       | 95184       | 97213       | 97173       |
| ...         | ...         | ...         | ...         |

(Note: Same as 25k, recommend using WebMap to select the desired grid.)

#### 100k Grid Numbers

| Grid Number | Grid Number | Grid Number | Grid Number |
|-------------|-------------|-------------|-------------|
| 9319        | 9417        | 9516        | 9618        |
| 9320        | 9418        | 9517        | 9619        |
| 9420        | 9419        | 9518        | 9620        |
| 9421        | 9516        | 9519        | 9621        |
| 9520        | 9517        | 9521        | 9622        |
| 9522        | 9518        | 9523        | 9623        |
| 9618        | 9519        | 9621        | 9720        |
| 9621        | 9520        | 9623        | 9721        |
| 9720        | 9521        | 9722        | 9723        |
| 9723_1      | 9723_2      | 9723_3      | 9723_4      |

### Retrieve Data by County ID

You can retrieve data by using the county ID:

- **URL Format:** 
```plaintext
https://cloudrun-zjoivcfvsa-uc.a.run.app/{county_id}
```

#### County IDs

| County Name | County ID | County Name | County ID |
|-------------|-----------|-------------|-----------|
| 連江縣       | 09007     | 嘉義市       | 10020     |
| 宜蘭縣       | 10002     | 嘉義縣       | 10010     |
| 彰化縣       | 10007     | 金門縣       | 09020     |
| 南投縣       | 10008     | 高雄市       | 64000     |
| 雲林縣       | 10009     | 臺東縣       | 10014     |
| 基隆市       | 10017     | 花蓮縣       | 10015     |
| 臺北市       | 63000     | 澎湖縣       | 10016     |
| 新北市       | 65000     | 新竹市       | 10018     |
| 臺中市       | 66000     | 新竹縣       | 10004     |
| 臺南市       | 67000     | 屏東縣       | 10013     |
| 桃園市       | 68000     | 苗栗縣       | 10005     |

### Retrieve Data by Grid Number and Feature Class

You can also retrieve specific data by using both the grid number and the feature class:

- **URL Format:** 
```plaintext
https://cloudrun-zjoivcfvsa-uc.a.run.app/{grid_number}/{feature_class}
```

This URL can be used in AGOL (ArcGIS Online).

### Feature Classes
For example: 
- **Bridge line**: `bridgel`
- **Building Area**: `builtupa`
- **Transportation Point**: `transp`

# Use Case
Shown below, are some exmaples of retrieving information on **applications in LeanIX** using a `allFactSheets` **base query** and a **variables template**. 

### General Data Retrievel and Implementation Concept
![img](/README%20&%20Documenation%20assets/general_implemntation_concept_with_code_diagram.png)

<br>
The data is retrieved in four main functions/steps:

- query function, i.e. `query_apps`: Reads query from text file and constructs the query by adding/adjusting filter components.
- post function i.e. `post_query`: Posts query to LeanIX and returns a parsed response (json), `post_query` is called/used within `query_apps`.
- transforming function i.e. `factSheets_to_df`: Creates a pandas data frame out of the parsed response.
- get function, i.e. `get_apps`: Is composed out of two functions: `query_apps` and `factSheets_to_df`. 
  - `get_apps` can be adjusted to suit the use case by passing different arguments to the functions: `query_apps`, `factSheets_to_df`. 

*You can find the diagram above in [README & Documentation assets](/README%20&%20Documenation%20assets/) folder.*

#### Main Functions
----------
```python
# get apps id (=LeanIX_ID), bankId, displayName
def get_apps(facet_filters: FilterTemplate=None, on_app_nodes: list=None, on_node_nodes: list=None) -> pd.DataFrame:
  
    return factSheets_to_df(query_apps(query_filters, on_app_nodes)).dropna()
```
```python
# Convert all factSheets of apps to df
def factSheets_to_df(allFactSheets : dict) -> pd.DataFrame:

    # get all nodes of the factSheet
    nodes = allFactSheets['data']['allFactSheets']['edges']
    df = json_normalize(nodes)

    # clean df column names by removing the prefix "node." from the name of the columns, e.g. node.displyName --to--> displayName
    df.columns = [col_name.removeprefix("node.") for col_name in df]
    return df
```
```python
# query app (LeanIX_IDs, bankId, name) with help of a GQL query stored in .txt file
def query_apps(facet_filters: dict=None, on_app_nodes: list=None, on_node_nodes: list=None) -> dict:
    # read query from file
    QUERY_PATH = f"{QUERIES_DIR}/apps.txt"
    query_data = _convert_gql_query_from_txt(QUERY_PATH)

    # apply facet filters when given
    if facet_filters:
        applied_filters = _apply_filters_to_query_variables(facet_filters)
        query_data["variables"] = _replace_query_variables(query_data["variables"], applied_filters)
    else:
        query_data["variables"] = _replace_query_variables(query_data["variables"], "")

    # add on-factSheet-nodes (Application's nodes) to query
    if on_app_nodes:
       query_data["query"] = _add_on_factSheet_nodes(query_data["query"], on_app_nodes)

    if on_node_nodes:
       query_data["query"] = _add_on_node_nodes(query_data["query"], on_node_nodes)

    # remove all query parts within and including hastags using regex, e.g.: #abs# --> abs
    # to ensure query syntax is correct when no facetFilters are given
    query_data["query"] = _clean_query(query_data["query"])

    # print query
    #print(":::::: query ::::::\n", query_data["query"])
    #print(":::::: variables ::::::\n", query_data["variables"])

    apps = post_query(query_data["query"], query_data["variables"])

    return apps
```
```python 
def post_query(gql_query: str, gql_variables: str=None) -> dict:
    # differentiate between queries with variables and queries without variables
    if gql_variables:
        data = {'query': gql_query, 'variables': gql_variables}
    else:
        data = {'query': gql_query}

    response = requests.post(
        url= lix.URLS.leanix_graphql, # get base URL for LeanIX GrpahQL API
        headers={'Authorization': f'Bearer {ACCESS_TOKEN}'},
        data=json.dumps(data)    
    )
    
    log.info(f"graphql query response code: {response.status_code}")
    # Raises HTTP Error, if one occurs.
    response.raise_for_status()
    # convert response content (text) to a dict with json.loads()
    parsed_response = json.loads(response.text)
    return parsed_response
```

<br>

### Use Case Examples 

**Use Case 1**: Retrieve some information on the factSheet type = `Application` in LeanIX, namely the `id`(=LeanIX_ID), `bankId`, `displayName`.


#### Function
----------
```python
# get id, bankId, displayName
def get_app_ids() -> pd.DataFrame:
    return get_apps()
```

#### Base Query (in .txt file)
----------
```gql
query allFactSheetsQuery($filter: FilterInput!, $sortings: [Sorting]) {
  allFactSheets(filter: $filter, sort: $sortings) {
    totalCount
    edges {
      node {
        ... on Application {
          id
          bankId
          displayName
          #ADDTIONAL_FACTSHEET_NODES#
        }
        #ADDTIONAL_NODE_NODES#
      }
    }
  }
}
```

#### Query Variables (in .txt file)
----------
```json
{
  "filter": {
    "facetFilters": [
      ${facet_filters}
    ]
  },
  "sortings": [
    {
      "key": "displayName",
      "order": "asc"
    }
  ]
}
```

#### Output
------
```json
{
"data": {
    "allFactSheets": {
      "edges": [
        {
          "node": {
            "id":"XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX",
            "bankId": "XXX",
            "displayName": "XXX XXXXX"
          }
        },
        {
          "node": {
            "id":"XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX",
            "bankId": "XXX",
            "displayName": "XXX XXXXX"
          }
        },
        {
          "node": {
            "id":"XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX",
            "bankId": "XXX",
            "displayName": "XXX XXXXX"
          }
        },
        ...
        ...
        ...
```
<br>

**Use Case 2**: Retrieve more information on the factSheet type = `Application` in LeanIX, namely the `apptype` and state of the application's `qualitySeal`.

**In Code** 
- In `allFactSheets` **base query**:  `#ADDTIONAL_FACTSHEET_NODES#` is replaced with `apptype` and `qualitySeal`.
**HOW? -->** Using [Regular Expression (regex)](https://docs.python.org/3/library/re.html)
- In `allFactSheets` **variables template**: `${facet_filters}` is replaced by a custom `facetFilters` template stored in a dictionary `filter_templates`, namely `fact_sheet_type`. 

  In `fact_sheet_type` filter the`FactSheetType` value is set to `Application` . 

  *NOTE*: Specifing the `FactSheetType` to `Application` ensures that only applications are retrieved and no empty `nodes` or other types of `FactSheets` (-> accurate and more efficient).
  
  See [`facetFilters` templates](#facetfilters-templates-fact_sheet_type-quality_seal) below.
 
<br>

#### Function
----------
```python
# get [id, bankId, displayName, apptype, qualitySeal] of the applications
def get_app_types_and_quality_seal() -> pd.DataFrame:
    return get_apps(facet_filters={"fact_sheet_type": {"keys":["Application"]}},  on_app_nodes=["apptype", "qualitySeal"])
```

#### Query with additional *on-factSheet-nodes*
----------
```gql
query allFactSheetsQuery($filter: FilterInput!, $sortings:[Sorting]) {
  allFactSheets(filter:$filter, sort:$sortings) {
    totalCount
    edges {
      node {
        ... on Application {
          id
          bankId
          displayName
          apptype
          qualitySeal
        }
        #ADDTIONAL_NODE_NODES#
      }
    }
  }
}
```

#### Query Variables (same as in Use Case 1!)
----------
```json
{
  "filter": {
    "facetFilters": [
      {
        "facetKey": "FactSheetTypes",
        "keys": [
          "Application"
        ]
      }
    ]
  },
  "sortings": [
    {
      "key": "displayName",
      "order": "asc"
    }
  ]
}
```
#### Output
----------
```json
{
"data": {
    "allFactSheets": {
      "edges": [
        {
          "node": {
            "id":"XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX",
            "bankId": "XXX",
            "displayName": "XXX XXXXX",
            "apptype": "service",
            "qualitySeal": "BROKEN",
          }
        },
        {
          "node": {
            "id":"XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX",
            "bankId": "XXX",
            "displayName": "XXX XXXXX",
            "apptype": "web_app",
            "qualitySeal": "APPROVED"
          }
        },
        {
          "node": {
            "id":"XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX",
            "bankId": "XXX",
            "displayName": "XXX XXXXX",
            "apptype": "XXXXX",
            "qualitySeal": "XXXXXXX"
          }
        },
        ...
        ...
        ...
```
<br>

**Use Case 3**: Same as before, retrieve the `id`, `bankId`, `displayName` and `apptype`. However, only of the applications with a `qualitySeal` == `BROKEN`  state. This is done by appling two`facetFilters`.

**In Code** 
- `allFactSheets` **base query**: Stays the same as in **Use Case 2**
- In `allFactSheets` **variables template**: `${facet_filters}` is replaced by two custom `facetFilters` templates stored in a dictionary `filter_templates`, namely `fact_sheet_type` and `quality_seal`. See   [`facetFilters` templates](#facetfilters-templates-fact_sheet_type-quality_seal) below.
<br> 

  In `fact_sheet_type` filter the`FactSheetType` value is set to `Application` and in `quality_seal` filter, the `keys` of `facetKey: DataQuality` is specified to `_qualitySealBroken_`. 

  **HOW? -->** Using [Python Template Strings](https://docs.python.org/3/library/string.html#template-strings)


    *NOTE*: Specifing the `FactSheetType` to `Application` ensures that only applications are retrieved and no empty `nodes` or other types of `FactSheets` (-> accurate and more efficient).



#### FacetFilters templates: `fact_sheet_type`, `quality_seal`
----------
```gql
# Filter templates listed
filter_templates = {"fact_sheet_type": fil_temp.fact_sheet_type_filter, 
                    "quality_seal": fil_temp.quality_seal_filter, 
                    "subscriptions": fil_temp.subscriptions_filter, 
                    "licence": fil_temp.licence_filter,
                    "lifecycle": fil_temp.lifecycle_filter,
                    "date_range": fil_temp.date_range_filter,
                    ...
                    ...
                    }

----------------------------------------------------------------------------

# Filter templates used in this demonstartion
fact_sheet_type_filter = {
        "facetKey": "FactSheetTypes",
        "operator": "OR",
        "keys": [
          "${keys}"
        ]
      }

quality_seal_filter = {
      "facetKey": "lxState", 
      "operator": "OR", 
      "keys": [
        "${keys}"
        ]
      }
```
`${keys}` is the placeholder to be replaced according to the use case. 


#### Function
----------
```python
# get [id, bankId, displayName, apptype, qualitySeal] of apps with a broken quality_seal
def get_app_types_and_quality_seal_broken() -> pd.DataFrame:
    return get_apps(facet_filters={"fact_sheet_type": {"keys":["Application"]}, "quality_seal": {"key":["_qualitySealBroken_"]}}, on_app_nodes=["apptype", "qualitySeal"])
```

#### Query with additional *on-factSheet-nodes* (same as in Use Case 2)
----------
```gql
query allFactSheetsQuery($filter: FilterInput!, $sortings:[Sorting]) {
  allFactSheets(filter:$filter, sort:$sortings) {
    totalCount
    edges {
      node {
        ... on Application {
          id
          bankId
          displayName
          apptype
          qualitySeal
        }
        #ADDTIONAL_NODE_NODES#
      }
    }
  }
}
```

#### Query Variables with `facetFilters` added
---------
```json
{
  "filter": {
    "facetFilters": [
      {
        "facetKey": "FactSheetTypes",
        "keys": [
          "Application"
        ]
      },
      {
        "facetKey": "DataQuality",
        "keys": [
          "_qualitySealBroken_"
        ]
      }
    ]
  },
  "sortings": [
    {
      "key": "displayName",
      "order": "asc"
    }
  ]
}
```

#### Output
----------
```json
{
"data": {
    "allFactSheets": {
      "edges": [
        {
          "node": {
            "id":"XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX",
            "bankId": "XXX",
            "displayName": "XXX XXXXX",
            "apptype": "service",
            "qualitySeal": "BROKEN",
          }
        },
        {
          "node": {
            "id":"XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX",
            "bankId": "XXX",
            "displayName": "XXX XXXXX",
            "apptype": "web_app",
            "qualitySeal": "BROKEN"
          }
        },
        {
          "node": {
            "id":"XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX",
            "bankId": "XXX",
            "displayName": "XXX XXXXX",
            "apptype": "XXXXX",
            "qualitySeal": "BROKEN"
          }
        },
        ...
        ...
        ...
```

<br>

### Modularity Benefits 
The modularity of this implementation facilitates the use and adjustement of queries and their variables to suit the desired use case.

Additional information can be retrievied by replacing `#ADDTIONAL_NODE_NODES#` with further nodes/inforamtion similar to how `#ADDTIONAL_FACTSHEET_NODES#` was replaced in this use case 2. 

Furthermore, a `date_range` filter can be applied to the query when needed by specifing a start and end date, `from` - `to`.

#### `date_range` Filter Template
```gql
date_range_filter =  {
    "dateFilter": {
        "type": "RANGE",
        "from": "${_from}",
        "to": "${_to}"
        }
    }
```

<br>

**Use Case 4**: Similar to the examples above, retrieve the `id`, `bankId`, `displayName` and the status of the apps `lifecycle`.

**In Code** 
- In `allFactSheets` **base query**: 
  
  `#ADDTIONAL_FACTSHEET_NODES#` is replaced with `apptype` and `qualitySeal`.

  `#ADDTIONAL_NODE_NODES#` is replaced with `status` and `createdAt`.

  **HOW? -->** Using [Regular Expression (regex)](https://docs.python.org/3/library/re.html).
- In `allFactSheets` **variables template**: 

  `${facet_filters}` is replaced by three custom `facetFilters` templates stored in a dictionary `filter_templates`, namely `fact_sheet_type` and `lifecycle` with a `date_range` filter. See [`facetFilters` templates](#facetfilters-templates-fact_sheet_type-quality_seal) below.
<br> 

  In `fact_sheet_type` filter the `FactSheetType` value is set to `Application` and in `lifecycle` filter the `keys` is specified to `_noLifecycle_`. 
  
  In `date_range` the value of `from` ist set to `2022-01-01` and that of `to` is set to `2024-01-01`. 

  **HOW? -->** Using [Python Template Strings](https://docs.python.org/3/library/string.html#template-strings)


    *NOTE*: There are multiple ways to query for information. For example `__missing__` can also be used instead of `_noLifecycle_` in the `lifecycle` filter template.

#### Function
----------
```python
# get id, bankId, displayName, apptype, qualitySeal, status, createdAt of apps with a no lifecycle between 2022-01-01 and 2024-01-01
def get_app_types_and_quality_seal_broken() -> pd.DataFrame:
    return get_apps(facet_filters={"fact_sheet_type": {"keys":["Application"]}, "lifecycle": {"key":["_noLifecycle_"], "date_range":["2022-01-01", "2024-01-01"]}}, on_app_nodes=["apptype", "qualitySeal"], , on_node_nodes=["status", "createdAt"])
```

#### Query with additional *on-factSheet-nodes* and *on-node-nodes*
----------
```gql
query allFactSheetsQuery($filter: FilterInput!, $sortings:[Sorting]) {
  allFactSheets(filter:$filter, sort:$sortings) {
    totalCount
    edges {
      node {
        ... on Application {
          id
          bankId
          displayName
          apptype
          qualitySeal
        }
        status
        createdAt
      }
    }
  }
}
```

#### Query Variables with `facetFilters` added
---------
```json
{
  "filter": {
    "facetFilters": [
      {
        "facetKey": "FactSheetTypes",
        "keys": [
          "Application"
        ]
      },
      {
        "facetKey": "lifecycle",
        "keys": [
          "_noLifecycle_"
        ],
        "dateFilter": {
          "type": "RANGE",
          "from": "2023-01-01",
          "to": "2029-12-31"
        }
      }
    ]
  },
  "sortings": [
    {
      "key": "displayName",
      "order": "asc"
    }
  ]
}
```

#### Output
----------
```json
{
  "data": {
    "allFactSheets": {
      "edges": [
        {
          "node": {
            "id":"XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX",
            "bankId": "XXX",
            "displayName": "XXX XXXXX",
            "apptype": "web_app",
            "qualitySeal": "BROKEN",
            "status": "ACTIVE",
            "createdAt": "2023-08-23T05:23:14.576182Z"
          }
        },
        {
          "node": {
            "id":"XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX",
            "bankId": "XXX",
            "displayName": "XXX XXXXX",
            "apptype": null,
            "qualitySeal": "BROKEN",
            "status": "ACTIVE",
            "createdAt": "2020-10-13T08:15:13.946941Z"
          }
        },
        {
          "node": {
            "id":"XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX",
            "bankId": "XXX",
            "displayName": "XXX XXXXX",
            "apptype": "client_app",
            "qualitySeal": "BROKEN",
            "status": "ACTIVE",
            "createdAt": "2023-08-23T07:04:07.328096Z"
          }
        },
        ...
        ...
        ...
```
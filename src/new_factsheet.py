 
"""
This file contains utility functions to create new FactSheets of type `Application` in LeanIX using LeanIX GraphQL API.

**Note**: 
    - API tokens are required to access LeanIX services. These should be placed in the `.env` file in the root directory.
    - **It is recommended to experiment using the `LEANIX_API_TOKEN_SANDBOX` before applying any changes using `LEANIX_API_TOKEN`**.
        In`.env` file:
        - `LEANIX_API_TOKEN_SANDBOX`: API Token for Sandbox 
        - `LEANIX_API_TOKEN`: API Token

**Dependencies**: 
    - `graphql_leanix_utils.py`
"""

import time
from typing import TypedDict
import graphql_leanix_utils as gqlix

########################## Variables / Custom Classes ##########################

# custom TypedDict 
class LifecyclePhaseDict(TypedDict):
    """
    A custom typed dictionary for adding new lifecycles 
    keys:
    ----
        type: str=None
        startDate: str=None
    """
    type: str=None
    startDate: str=None

class SubscriptionDict(TypedDict):
    """
    A custom typed dictionary for adding new subscriptions 
    keys:
    ----
        factSheet_id: str
        user_email: str
        user_roles: list
        role_type: str= "RESPONSBILE"
    """
    factSheet_id: str
    user_email: str
    user_roles: list
    role_type: str= "RESPONSBILE"

class FactSheetAttributeDict(TypedDict):
    """
    A custom typed dictionary for adding new attributes 
    keys:
    ----
        attribute_name: str
        attribute_value: str
    """
    attribute_name: str
    attribute_value: str

########################## Variables / Custom Classes ##########################


########################## GraphQL Queries ##########################

def _new_app_query(name: str, type: str, apptype: str, description: str, businessCriticality: str, functionalSuitability: str, 
                   datamaster: bool, user_groups_ids: list, ITComponents_ids: list, lifecycle_phase: LifecyclePhaseDict,
                   additional_app_attributes: list=None):
    """Creates a new query with help of a GQL query template stored in `.txt` file

        Parameters:
            name (str): 
                name of factSheet in LeanIX
            type (str): 
                type of factSheet in LeanIX
            description (list): 
                description of factSheet in LeanIX
            bussinessCriticality (str):
                businessCriticality can have five different keys: 
                ["__missing__", "administrativeService", "businessCritical", "businessOperational", "missionCritical"]
            functionalSuitability (str):
                functional_suitability can have five different keys: 
                ["__missing__", "appropriate", "insufficient", "perfect", "unreasonable"]
            datamaster (bool):
                datamaster (Speicherung DSG relevante Daten) of factSheet in LeanIX
            user_groups_ids (list):
                List of UserGroups to be linked to Application 

                *Note*: UserGroups can only be added using their LeanIX Ids
            ITComponents_ids (list):
                List of ITComponents to be linked to Application 
                
                *Note*: ITComponentscan only be added using their LeanIX Ids
            lifecylce_phase (LifecyclePhaseDict):
                Specify lifecycle phase using a custom TypedDict LifecyclePhaseDict (see Example in `create_new_app()` docstring)
            additional_app_attributes (list[FactSheetAttributeDict], optional): 
                Add additional attributes to factSheet
                Specify additional attributes using a custom TypedDict (see Example in `create_new_app()` docstring)

        Returns:
            post_query (dict):
                GraphQL query
    """
   
    QUERY_PATH = f"{gqlix.QUERIES_DIR}/create_app_factsheet_template.txt"
    query_data = gqlix._convert_gql_query_from_txt(QUERY_PATH)
    query = str(query_data["query"]) 
    variables = str(query_data["variables"])
    
    # add name, description, apptype 
    variables = variables.replace("#FACT_SHEET_NAME#", name).replace("#FACT_SHEET_TYPE#", type).replace("#FACT_SHEET_DESCRIPTION#", description).replace("#APP_TYPE#", apptype)
    # add businessCriticality, functional_suitability
    variables = variables.replace("#BUSINESS_CRITICALITY#", businessCriticality).replace("#FUNCTIONAL_SUITABILITY#", functionalSuitability)

    # add UserGroups and IT-Components
    _user_groups = add_user_groups(ids= user_groups_ids)
    _ITComponents = add_ITComponents(ids= ITComponents_ids)
    variables = variables.replace("#ADD_USER_GROUPS#", _user_groups).replace("#ADD_ITCOMONENTS#", _ITComponents).replace("#PHASE_TYPE#", lifecycle_phase["type"]).replace("#START_DATE#", lifecycle_phase["startDate"])
        
    # specify dsg (Datenschutz: Werden in der Applikation besonders schützenswerte Daten verarbeitet oder gespeichert?)
    if datamaster: variables = variables.replace("#DATAMASTER#", "False") 
    else: variables = variables.replace("#DATAMASTER#", "True")

    # add additional attributes if given
    variables = variables.replace("#ADD_APP_ATTRIBUTES#", additional_app_attributes)

    variables = variables.replace("\'", "\"")

    post_query = gqlix.post_query(query, variables)
    print("-------------------CREATE FACTSHEET QUERY------------------------")
    gqlix.print_query(query, variables)
    print("-------------------CREATE FACTSHEET QUERY------------------------\n")
    return post_query

########################## GraphQL Queries ##########################


########################## Create new Application FactSheet ##########################

def create_new_app_from_query_file(query_file: str):
    """Reads GraphQL query from a `.txt `file and post the query to create a factSheet of type `Application`
        
        Parameters:
            query_file (str): 
                The name of the query file
                
        Returns:
            parsed_response (dict):
                Content of the query response as python dictionary
        Note:
        -----
        - The query file must be in directory `queries_txt`
        - The query variables and actual query body must be separated by an empty line
        
        Examples:
            Create a new factSheet `Application` using the file `create_factsheet_from_query.txt` in the dierctory `queries_txt`
            >>> factsheet_from_query = nf.create_new_app_from_query_file(query_file= "create_factsheet_from_query")  
    """

    response = gqlix.post_query_from_file(file_name= query_file)
    print("Posted Query Variables:", response)
    return response

def create_new_app(name: str, type: str, apptype: str, description: str, businessCriticality: str, functionalSuitability: str, datamaster: bool, 
                    subscriptions: SubscriptionDict, user_groups_ids: list, ITComponents_ids: list, 
                    lifecycle_phase: LifecyclePhaseDict, additional_app_attributes: list[FactSheetAttributeDict]=None):
    """Creates a new FactSheet of type `Application` in LeanIX

        Parameters:
            name (str): 
                name of factSheet in LeanIX
            type (str): 
                type of factSheet in LeanIX
            description (list): 
                description of factSheet in LeanIX
            bussinessCriticality (str):
                businessCriticality can have five different keys: 
                ["__missing__", "administrativeService", "businessCritical", "businessOperational", "missionCritical"]
            functionalSuitability (str):
                functional_suitability can have five different keys: 
                ["__missing__", "appropriate", "insufficient", "perfect", "unreasonable"]
            datamaster (bool):
                datamaster (Speicherung DSG relevante Daten) of factSheet in LeanIX
            subscriptions (SubscriptionDict):
                A list of subscription role ids that have to be assigned to the new subscription
                Specify subscriptions using a custom TypedDict SubscriptionDict (see Example)
                Possible roles are: 
                "AV Fachlich" = "7d3da7df-89d0-4e72-a61b-5693cfdf33ff"
                "AV Technisch" = "6f8aa477-1b9b-44b7-af6c-237c25e5adf0"
                "GPV" = "99c9c884-b163-4d0c-993f-10c95b04e859"
                Possible role_types are: 
                    Type of role to be assigned: ["RESPONSBILE", "ACCOUNTABLE", "OBSERVER"]
            user_groups_ids (list):
                List of UserGroups to be linked to Application 

                *Note*: UserGroups can only be added using their LeanIX Ids
            ITComponents_ids (list):
                List of ITComponents to be linked to Application 
                
                *Note*: ITComponentscan only be added using their LeanIX Ids
            lifecylce_phase (LifecyclePhaseDict):
                Specify lifecycle phase using a custom TypedDict LifecyclePhaseDict (see Example)
            additional_app_attributes (list[FactSheetAttributeDict], optional): 
                Add additional attributes to factSheet
                Specify additional attributes using a custom TypedDict (see Example)

        Returns:
            tuple[create_app_query (dict), create_subscription_query (dict)]:

        Example:
            Create a new `Application` FactSheet with additional attributes 

            >>> # businessCriticality can have five different keys: ["__missing__", "administrativeService", "businessCritical", "businessOperational", "missionCritical"]
            >>> # Specify the businessCriticality
            >>> _businessCriticality = "administrativeService"

            >>> # functional_suitability can have five different keys: ["__missing__", "appropriate", "insufficient", "perfect", "unreasonable"]
            >>> # Specify the functionalSuitabilityt
            >>> _functionalSuitability = "appropriate"

            >>> # UserGroups can only be added using their LeanIX Id
            >>> # specify a list of UserGroups to be linked 
            >>> _user_groups_ids = ["43abXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX", "b990XXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX"]

            >>> # ITComponents can only be added using their LeanIX Id
            >>> # specify list of ITComponents to be linked 
            >>> _ITComponents_ids = ["231XXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX", "f087XXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX"]

            >>> # Specify the lifecycle phase using a custom TypedDict
            >>> _lifecycle_phase : nf.LifecyclePhaseDict = {"type": "active", "startDate": "2021-01-01"}

            >>> # Specify subscriptions using a custom TypedDict
            >>> # Note: "factSheet_id" is not nedeed in this case (in method "create_new_app()") because we are creating a new FactSheet.
            >>> #       Check method "create_new_app()" for implementation details
            >>> _subscriptions : nf.SubscriptionDict = {"factSheet_id": "", "user_email": "max.mustermann@bank.com", 
                                                "role_type": "RESPONSIBLE", 
                                                "user_roles":["7d3dXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX", "6f8aXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX"]}

            >>> # Add additional attributes 
            >>> # Specify additional attributes using a custom TypedDict
            >>> # Example: Add attribute "completeClientDatabase = no" (Kundendatenumfang) and "massDataQueries = no" (Massendatenabfragen)

            >>> # datamaster (Datenschutzgesetz) can have five different keys: ["False", "True", "__missing__"]
            >>> # completeClientDatabase (Kundendatenumfang) can have five different keys: ["False", "True", "__missing__"]
            >>> _completeClientDatabase: nf.FactSheetAttributeDict={"attribute_name": "completeClientDatabase", "attribute_value": "no"}
            >>> # massDataQueries (Massendatenabfragen) can have different keys: ["yes", "no", "__missing__", "export"]
            >>> _massDataQueries: nf.FactSheetAttributeDict={"attribute_name": "massDataQueries", "attribute_value": "no"}
            >>> # deletionProcess (Löschmechanismus) can have five different keys: ["__missing__", "none", "singleDeletion", "massDeletion"]
            >>> _deletionProcess: nf.FactSheetAttributeDict={"attribute_name": "deletionProcess", "attribute_value": "massDeletion"}
            >>> # holdOffTime (Vorhaltezeit) can have five different keys: ["__missing__", "notApplicable", "equalOrLessThan3Months", "equalOrLessThan12Months", "greaterThan12Months"]
            >>> _holdOffTime : nf.FactSheetAttributeDict={"attribute_name": "holdOffTime", "attribute_value": "equalOrLessThan3Months"}
            >>> # personDataProtectionAgreements (Vereinbarung zur Datensicherheit und Datenschutz mit Externen) can have five different keys: ["notRequired", "__missing__", "inPlace", "notInPlace", "onParent"]
            >>> _personDataProtectionAgreements : nf.FactSheetAttributeDict={"attribute_name": "personDataProtectionAgreements", "attribute_value": "notRequired"}
            >>> _additonal_app_attributes = [_completeClientDatabase, _massDataQueries, _deletionProcess, _holdOffTime, _personDataProtectionAgreements]

            >>> _additonal_app_attributes = [_completeClientDatabase, _massDataQueries, _deletionProcess, _holdOffTime, _personDataProtectionAgreements]

            >>> new_app_factSheet_2 = nf.create_new_app(name= "_TEST CREATE NEW Application From Template With Additional Attributes", 
            >>>                         type= "Application", apptype="web_app", description= "Description ...", 
            >>>                         businessCriticality= _businessCriticality, functionalSuitability= _functionalSuitability,
            >>>                         datamaster= False, subscriptions= _subscriptions,
            >>>                         user_groups_ids= _user_groups_ids,
            >>>                        ITComponents_ids= _ITComponents_ids, 
            >>>                         lifecycle_phase=_lifecycle_phase,
            >>>                         additional_app_attributes=_additonal_app_attributes)

            >>> new_app_factSheet_2
    """

    # add additional attributes if given
    _additional_app_attributes = """"""
    if additional_app_attributes: 
        for variable in additional_app_attributes:
            _additional_app_attributes += add_on_app_attribute(variable)
            
    create_app_query = _new_app_query(name=name, type=type, apptype=apptype, description=description, 
                                    businessCriticality=businessCriticality, functionalSuitability=functionalSuitability,
                                    datamaster=datamaster, user_groups_ids=user_groups_ids, ITComponents_ids=ITComponents_ids, 
                                    lifecycle_phase=lifecycle_phase, additional_app_attributes=_additional_app_attributes)

    time.sleep(5) # delay for 5 seconds for the new app to be created 

    # get the id of the newly create app
    new_app_id = gqlix.get_app_id_by_name(name) # raises an error if name is not found

    # ignore and replace subscriptions["factSheet_id"] 
    # This step is needed in this function because we create a new application factSheet on LeanIX (not needed if the application already exists on LeanIX)
    subscriptions["factSheet_id"] = new_app_id 

    create_subscription_query = add_subscriptions(factSheet_id= subscriptions["factSheet_id"], user_email=subscriptions["user_email"], user_roles=subscriptions["user_roles"], role_type=subscriptions['role_type'])

    return create_app_query, create_subscription_query

########################## Create new Application FactSheet ##########################


########################## Common/Helper Methods ########################## 
def add_subscriptions(factSheet_id: str, user_email: str, user_roles: list, role_type: str= "RESPONSBILE",):
    """Adds a new Subcription to a FactSheet

            Parameters:
                factSheet_id (str): 
                    Id of the factSheet in LeanIX
                user_email (str): 
                    Email of the person to be subscriped (be added as subscription)
                user_roles (list): 
                    A list of subscription role ids that have to be assigned to the new subscription
                    Possible roles are: 
                    "AV Fachlich" = "7d3dXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX"
                    "AV Technisch" = "6f8aXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX"
                    "GPV" = "99c9XXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX"

                role_type (str): 
                    Type of role to be assigned: ["RESPONSBILE", "ACCOUNTABLE", "OBSERVER"]
                
            Returns:
                parsed_response (dict):
                    Content of the query response as python dictionary
            Note:
            -----
            - LeanIX extracts the first and last name of the subscriper automatically from the `user_email` 
            
            Examples:
                Add a subscription to factSheet: "Test App" with following attributes: first_name, last_name, email, RESPONSIBLE, user_roles: "AV Fachlich", "AV Technisch"
                >>> create_subscriptions(factSheet_id= "XXXX2e4-XXXX-XXXX-XXXX-XXXXXXXXXXXX", user_email= "first_name.last_name@bank.com", role_type="RESPONSIBLE", user_roles= ["7d3dXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX", "6f8aXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX"])
    """

    QUERY_PATH = f"{gqlix.QUERIES_DIR}/create_factsheet_subscription.txt"
    query_data = gqlix._convert_gql_query_from_txt(QUERY_PATH)

    query_data["query"] = str(query_data["query"]).replace(
        "#FACT_SHEET_ID#", factSheet_id).replace("#USER_EMAIL#", user_email).replace(
            "#ROLE_TYPE#", role_type).replace("#ROLE_IDS#", f"{user_roles}").replace("\'", "\"")
    print(":::::: final post query ::::::\n", query_data["query"])

    query = gqlix.post_query(query_data["query"], query_data["variables"])
    return query

def add_user_groups(ids: list) -> str:
    """Adds new UserGroup to a FactSheet

            Parameters:
                ids (list): 
                    Ids of the UserGroups to be added
            Returns:
                user_groups (str):
                    Variable/Filter to be added to the GraphQL query variables
    
            Note:
            -----
                - purpose of having `new_#NUMBER#` in the path is 
                to add a suffix to relations in the following format `/new_NUMBER` e.g. `/new_1`.
                
                A suffix must be added to the path values and it must be unique for each relation 
    """

    template = """
    {
      "op": "add",
      "path": "/relApplicationToUserGroup/new_#NUMBER#",
      "value": "{\\"factSheetId\\":\\"#USER_GROUP_ID#\\"}"
    },"""
    
    user_groups = """"""
    number = 0
    for id in ids:
        number += 1
        user_groups += template.replace("#USER_GROUP_ID#", id).replace("#NUMBER#", str(number))

    return user_groups

def add_ITComponents(ids: list):
    """Adds new ITComponents to a FactSheet

            Parameters:
                ids (list): 
                    Ids of the ITComponents to be added
            Returns:
                ITComponents (str):
                    Variable/Filter to be added to the GraphQL query variables
    
            Note:
            -----
                - purpose of having `new_#NUMBER#` in the path is 
                to add a suffix to relations in the following format `/new_NUMBER` e.g. `/new_1`.
                
                A suffix must be added to the path values and it must be unique for each relation 
    """
    
    template = """
    {
      "op": "add",
      "path": "/relApplicationToITComponent/new_#NUMBER#",
      "value": "{\\"factSheetId\\":\\"#ITCOMPONENT_ID#\\"}"
    },"""
    
    ITComponents = """"""
    number = 100 # to ensure having unique path suffix
    for id in ids:
        number += 1
        ITComponents += template.replace("#ITCOMPONENT_ID#", id).replace("#NUMBER#", str(number))

    return ITComponents

def add_on_app_attribute(attribute_dict: FactSheetAttributeDict):
    template = """
    {
      "op": "add",
      "path": "/#ATTRIBUTE_NAME#",
      "value": "#ATTRIBUTE_VALUE#"
    },"""

    template = template.replace("#ATTRIBUTE_NAME#", attribute_dict["attribute_name"]).replace("#ATTRIBUTE_VALUE#", attribute_dict["attribute_value"])
    print("Additional App Attributes: ", template)
    return template
########################## Common/Helper Methods ##########################



#Currently NOT USED!###################### Further functions that could be used for FactSheet like: Process, UserGroup, ...
def add_children(ids: list):
    """Adds new children FactSheet to another FactSheet

            Parameters:
                ids (list): 
                    Ids of the children FactSheets to be added
            Returns:
                children (str):
                    Variable/Filter to be added to the GraphQL query variables
    
            Note:
            -----
                - purpose of having `new_#NUMBER#` in the path is 
                to add a suffix to relations in the following format `/new_NUMBER` e.g. `/new_1`.
    """   
         
    template = """
    {
      "op": "add",
      "path": "/relToChild/new_#NUMBER#",
      "value": "{\\"factSheetId\\":\\"#CHILD_ID#\\"}"
    },"""
    
    children = """"""
    number = 200
    if ids != None:
        for id in ids:
            number += 1
            children += template.replace("#CHILD_ID#", id).replace("#NUMBER#", str(number))

    return children

def add_applications(ids: list):
    """Adds new Applications to a FactSheet

        Parameters:
            ids (list): 
                Ids of the Applications to be added
        Returns:
            apps (str):
                Variable/Filter to be added to the GraphQL query variables

        Note:
        -----
            - purpose of having `new_#NUMBER#` in the path is 
            to add a suffix to relations in the following format `/new_NUMBER` e.g. `/new_1`.
            
            A suffix must be added to the path values and it must be unique for each relation 
    """
  
    
    template = """
    {
      "op": "add",
      "path": "/relProcessToApplication/new_#NUMBER#",
      "value": "{\\"factSheetId\\":\\"#APP_ID#\\"}"
    },"""""
    
    apps = """"""
    number = 0
    if ids != None:
        for id in ids:
            number += 1
            apps += template.replace("#APP_ID#", id).replace("#NUMBER#", str(number))

    return apps
#Currently NOT USED!###################### Further functions that could be used for FactSheet like: Process, UserGroup, ...

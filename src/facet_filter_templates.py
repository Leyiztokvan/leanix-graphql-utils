"""
Facet Filter Templates 

Check the dictionary of different filter templates (bottom of the page)
"""

facet_key_filter ={
        "facetKey": "${facet_key}",
        "operator": "OR",
        "keys": [
          "${keys}"
        ]
      }

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

subscriptions_filter = {
        "facetKey": "Subscriptions",
        "keys": [
          "${keys}"
        ]
      }

licence_filter = {
        "facetKey": "43f2XXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX", 
        "operator": "OR",
        "keys": [
            "${keys}"
        ]
      }

# reporting_tag can have four different keys: ["__missing__", "layer 1". "layer 2", "layer 3"]
  # reporting_tag_layers = [ 
  # "4dc4XXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX", # layer 1
  # "658cXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX", # layer 2
  # "9564XXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX", # layer 3 ]
reporting_tag_filter = {
        "facetKey": "e278XXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX", 
        "operator": "OR",
        "keys": [
            "${keys}"
        ]
      }

# can have five different keys: ["__missing__", "administrativeService", "businessCritical", "businessOperational", "missionCritical"]
business_criticality_filter= {
        "facetKey": "businessCriticality", 
        "operator": "OR",
        "keys": [
            "${keys}"
        ]
      }

lifecycle_filter = {
        "facetKey": "lifecycle",
        "operator": "OR",
        "keys": [
          "${keys}"
        ]
      }

functional_suitability_filter = {
        "facetKey": "functionalSuitability", 
        "operator": "OR",
        "keys": [
            "${keys}"
        ]
      }

date_range_filter =  {
    "dateFilter": {
        "type": "RANGE",
        "from": "${_from}",
        "to": "${_to}"
        }
    }

IT_component_filter = {
        "facetKey": "relApplicationToITComponent",
        "operator": "OR",
        "keys": [
          "${keys}"
        ]
      }

############################################## Templates of Data filters (DSG Datenschutzgesetz)

# Data Protection Act (Datenschutzgesetz)
# keys = ["False", "True", "__missing__"]
dsg_datamaster_filter = {
        "facetKey": "datamaster",
        "operator": "OR",
        "keys": [
          "${keys}"
        ]
      }

# keys = ["False", "True", "__missing__"]
client_database_filter = {
        "facetKey": "completeClientDatabase",
        "operator": "OR",
        "keys": [
          "${keys}"
        ]
      }

# keys = ["yes", "no", "__missing__", "export"]
mass_data_filter = {
        "facetKey": "massDataQueries",
        "operator": "OR",
        "keys": [
          "${keys}"
        ]
      }

# keys = ["notRequired", "__missing__", "inPlace", "notInPlace", "onParent"]
person_data_protection_filter= {
        "facetKey": "personDataProtectionAgreements",
        "operator": "OR",
        "keys": [
          "${keys}"
        ]
      }

# keys = ["__missing__", "none", "singleDeletion", "massDeletion"]
data_deletion_process_filter= {
        "facetKey": "deletionProcess",
        "operator": "OR",
        "keys": [
          "${keys}"
        ]
      }


# keys = ["__missing__", "notApplicable", "equalOrLessThan3Months", "equalOrLessThan12Months", "greaterThan12Months"]
data_holdOffTime_filter= {
        "facetKey": "holdOffTime",
        "operator": "OR",
        "keys": [
          "${keys}"
        ]
      }

############################################## Templates for DATA 

# Template for Application FactSheet
relation_application_to_process_filter ={
        "facetKey": "relApplicationToProcess",
        "operator": "OR",
        "keys": [
          "${keys}"
        ],
      }

relation_application_to_user_group_filter ={
        "facetKey": "relApplicationToUserGroup",
        "operator": "OR",
        "keys": [
          "${keys}"
        ],
      }

relation_application_to_interface_filter ={
        "facetKey": "relConsumerApplicationToInterface",
        "operator": "OR",
        "keys": [
          "${keys}"
        ],
      }

# Template for UserGroup FactSheet

relation_to_parent_filter = {
        "facetKey": "relToParent",
        "operator": "OR",
        "keys": [
          "${keys}"
        ],
        "relationFieldsFilterOperator": "INCLUSIVE"
      }


# Template for Interface

relation_interface_to_provider_application_filter ={
        "facetKey": "relInterfaceToProviderApplication",
        "operator": "OR",
        "keys": [
          "${keys}"
        ],
      }


relation_interface_to_consumer_application_filter ={
        "facetKey": "relInterfaceToConsumerApplication",
        "operator": "OR",
        "keys": [
          "${keys}"
        ],
      }


# Templates for IT-Components

rel_ITComponent_to_application_filter = {
        "facetKey": "relITComponentToApplication",
        "operator": "OR",
        "keys": [
          "${keys}"
        ],
      }

rel_ITComponent_to_interface_filter = {
        "facetKey": "relITComponentToInterface",
        "operator": "OR",
        "keys": [
          "${keys}"
        ],
      }

relation_ITComponent_to_user_group_filter = {
        "facetKey": "relITComponentToUserGroup",
        "operator": "OR",
        "keys": [
          "${keys}"
        ],
      }

relation_ITComponent_to_provider_filter = {
        "facetKey": "relITComponentToProvider",
        "operator": "OR",
        "keys": [
          "${keys}"
        ],
      }

# dictionary of different filter templates
filter_templates = {"facet_key": facet_key_filter,
                    "fact_sheet_type": fact_sheet_type_filter, 
                    "quality_seal": quality_seal_filter, 
                    "subscriptions": subscriptions_filter, 
                    "licence": licence_filter,
                    "reporting_tag": reporting_tag_filter,
                    "business_criticality": business_criticality_filter,
                    "lifecycle": lifecycle_filter,
                    "date_range": date_range_filter,
                    "IT_component": IT_component_filter,
                    "relation_to_parent": relation_to_parent_filter,
                    "relation_interface_to_provider_application": relation_interface_to_provider_application_filter,
                    "relation_interface_to_consumer_application": relation_interface_to_consumer_application_filter,
                    "relation_ITComponent_to_application" : rel_ITComponent_to_application_filter,
                    "relation_ITComponent_to_interface" : rel_ITComponent_to_interface_filter, 
                    "relation_ITComponent_to_user_group" : relation_ITComponent_to_user_group_filter,
                    "relation_ITComponent_to_provider" : relation_ITComponent_to_provider_filter,
                    "relation_application_to_process" : relation_application_to_process_filter,
                    "relation_application_to_user_group" : relation_application_to_user_group_filter,
                    "relation_application_to_interface" : relation_application_to_interface_filter,
                    "dsg_datamaster" : dsg_datamaster_filter,
                    "client_database" : client_database_filter,
                    "person_data_protection" : person_data_protection_filter, #Massendatenabfragen
                    "functional_suitability" : functional_suitability_filter, #Fachliche Eignung
                    "mass_data": mass_data_filter,
                    "data_deletion_process": data_deletion_process_filter,
                    "data_holdOffTime" : data_holdOffTime_filter,
                    }
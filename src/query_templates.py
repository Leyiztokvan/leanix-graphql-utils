"""
Query Filter Templates
"""

interface_logEvents_by_id_query = """{allLogEvents(factSheetId: "FACT_SHEET_ID") {
          edges {
            node {
              id
              eventType
              path
              oldValue
              newValue
              secondsPast
                createdAt
                user {
                id
                displayName
                email
                technicalUser
                }
            }
          }
        }
      }""" 

app_tag_group_query ="""tags {
            id
            name
            color
            tagGroup {
              name
              shortName
            }
          }"""


app_subscriptions_query = """subscriptions {
            edges {
              node {
                id
                user {
                  id
                  displayName
                  email
                }
                roles {
                  name
                }
                type
                createdAt
              }
            }
          }"""

app_logEvents_by_id_query = """{allLogEvents(factSheetId: "FACT_SHEET_ID") {
          edges {
            node {
              id
              path
              newValue
              user {
                displayName
              }
              createdAt
            }
          }
        }
      }"""

bankID_query = """
    {
    factSheet(id: "FACT_SHEET_ID") {
        ... on Application {
            bankId
            }
      }
    }"""


apps_lifecycle_query = """ApplicationLifecycle: lifecycle {
            asString
            phases {
              phase
              startDate
            }
          }"""

############################################### Buisness Capability
bankID_business_capability_query = """
    {
    factSheet(id: "FACT_SHEET_ID") {
        ... on BusinessCapability {
            bankId
            }
      }
    }"""

all_bankID_business_capability_query = """{
    allFactSheets(
        factSheetType: BusinessCapability
        sort: {key: "bankId", order: desc}
    ) {
        edges {
            node {
                ... on BusinessCapability {
                    id
                    displayName
                    bankId
                }
            }
        }
    }
}"""

rel_to_parent_query = """relToParent {
            edges {
              node {
                factSheet {
                  displayName
                  id
                  type
                  level
                }
              }
            }
          }"""
############################################### Buisness Capability

############################################### IT Component
rel_ITComponent_to_app_query = """relITComponentToApplication {
            edges {
              node {
                id
                factSheet {
                  displayName
                  id
                }
              }
            }
          }"""


ITComponent_subscriptions_query = """subscriptions {
            edges {
              node {
                id
                user {
                  id
                  displayName
                  email
                }
                roles {
                  name
                }
                type
                createdAt
              }
            }
          }"""

ITComponent_lifecycle_query = """ITComponentLifecycle: lifecycle {
            asString
            phases {
              phase
              startDate
            }
          }"""

rel_ITComponent_to_provider_query = """relITComponentToProvider {
            edges {
              node {
                id
                factSheet {
                  displayName
                  id
                }
              }
            }
          }"""

rel_ITComponent_to_interface_query = """relITComponentToInterface {
            edges {
              node {
                id
                factSheet {
                  displayName
                  id
                }
              }
            }
          }"""

completion_query = """completion {
        percentage
        }"""
############################################### IT Component

############################################### Process
process_subscriptions_query = """subscriptions {
            edges {
              node {
                id
                user {
                  id
                  displayName
                  email
                }
                roles {
                  name
                }
                type
                createdAt
              }
            }
          }"""


process_rel_to_app_query = """relProcessToApplication {
            edges {
              node {
                id
                factSheet {
                  displayName
                  id
                  type
                }
              }
            }
          }"""

process_rel_to_parent_query = """relToParent {
            edges {
              node {
                factSheet {
                  displayName
                  id
                  type
                }
              }
            }
          }"""

############################################### Process



############################################### buisness_capability_bankId_importing_templates

highest_bankId_app = """{
    allFactSheets(
        factSheetType: BusinessCapability
        sort: {key: "bankId", order: desc}
        first: 1
    ) {
        edges {
            node {
                ... on BusinessCapability {
                    bankId
                }
            }
        }
    }
}"""

set_bankId_query =  """mutation ($patches: [Patch]!) {
    updateFactSheet(id: "#ID#", patches: $patches) {
        factSheet {
            id
            displayName 
            ... on BusinessCapability {
                bankId
            }
        }
    }
}"""


set_bankId_variables = """{
    "patches": [
        {
            "op": "replace",
            "path": "/bankId",
            "value": "#NEW_bankID#"
        }
    ]
}""" 

factSheet_status = """{
    factSheet(id: "#ID#") {
        status
    }
}"""

############################################### buisness_capability_bankId_importing_templates

"""
Script `get_and_set_bankId_for_buisness_capability` assigns a `bankId` to every `BusinessCapability` FactSheet

Note: This line must be uncommented `#if __name__ == "__main__":` for the script to run (to avoid unnecessary processing/behavior)
"""

import logging
import sys

import graphql_leanix_utils as gqlix
import query_templates as query_temp


# Logging setup
log = logging.getLogger(__name__)

def main():
    # 1. retrieve all Buisness Capability FactSheets
    business_capabilities = gqlix.get_business_capability()
    print(business_capabilities)

    print(business_capabilities["bankId"])

    last_bankId = get_max_bankId() 
    # 2. loop over all Buisness Capability FactSheets and set bankId
    for index, value in business_capabilities.iterrows():
            #print("BC_id:", value["id"])
            bc_id = value["id"]
        
            # Check if the Business Capability has status "ACTIVE"
            if get_status(bc_id) != "ACTIVE":
                log.info(f"Skipping archived Business Capability {value['displayName']} (id={bc_id}).")
                continue

            bankId = gqlix.query_bankId_business_capability(bc_id)["data"]["factSheet"]["bankId"]
            print("current_bankId:", bankId)

            # if bankId already exists, skip/continue
            if bankId:
                continue
            
            # set new bankId
            bankId = get_next_bankId(last_bankId)
            last_bankId = bankId
            
            if not set_bankId(bc_id, bankId):
                raise AttributeError(f"Failed to update Business Capability {value['displayName']} (id={bc_id})")

            log.info(f" Business Capability {value['displayName']} (id={bc_id}): bankId={bankId}")
                
bankId_prefix = "BC"


def get_max_bankId() -> str:
    graphql_query = query_temp.highest_bankId_app

    result = gqlix.post_query(graphql_query)

    if result == "":
        return result
    
    node = result["data"]["allFactSheets"]["edges"][0]["node"]
    return node["bankId"]


def get_next_bankId(bankId: str) -> str:
    # set a minimum value when bankId is empty
    if bankId == "":
        counter = 10 # minimum value
    else:
        counter = int(bankId[len(bankId_prefix):])

    # construct a bankId our of the prefix and 4 digits (example: BC0011)
    print(counter)
    bankId = bankId_prefix + '{:04d}'.format(counter + 1)
    print("new_bankId:", bankId)
    return bankId


def set_bankId(id: str, bankId: str) -> bool:
    graphql_query = query_temp.set_bankId_query.replace("#ID#", id)
    
    graphql_variables = query_temp.set_bankId_variables.replace("#NEW_bankID#", bankId)
    #print(graphql_query, graphql_variables)

    result = gqlix.post_query(graphql_query, graphql_variables)
    error = result.get('errors')
    if error:
        log.error(error)
        return False
    return True


def get_status(id: str) -> str:
    graphql_query = query_temp.factSheet_status.replace("#ID#", id)
    #print(graphql_query)
    
    result = gqlix.post_query(graphql_query)
    print("status:", result["data"]["factSheet"]["status"])
    return result["data"]["factSheet"]["status"]
    

#if __name__ == "__main__":
    try:
        main()
    except Exception:
        # Abnormal termination
        log.critical('An unhandled exception occured', exc_info=True)
        sys.exit(1)
    else:
        # Successful exit
        sys.exit(0)

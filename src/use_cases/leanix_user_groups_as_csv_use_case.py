"""This Script get all UserGroups in LeanIX of with parent `Bank` and saves the df as `.csv` files in the folder `data\user_group-organisation_from_parent_Bank`"""

import os 
import sys
# Build an absolute path from this notebook's parent directory
module_path = os.path.abspath(os.path.join('..'))
# Add `module_path` to sys.path if not already present
if module_path not in sys.path:
    sys.path.append(module_path)

#  import the desired module
import graphql_leanix_utils as gqlix
import pandas as pd

# LeanIX IDs of User Group/Organisation
user_groups_dict = {
    # level 1
    "BANK" : "XXXXXXXX-090f-XXXX-XXXX-XXXXXXXXXXXX",
    # level 2, parent : BANK  
    "Finanz- & Risikomanagement" : "XXXXXXXX-5ca7-XXXX-XXXX-XXXXXXXXXXXX",
    "Unternehmenskundenberatung" : "XXXXXXXX-ac49-XXXX-XXXX-XXXXXXXXXXXX",
    "Corporate Development & Sustainable Asset Management" : "XXXXXXXX-0e80-XXXX-XXXX-XXXXXXXXXXXX",
    "IT & Services" : "XXXXXXXX-6996-XXXX-XXXX-XXXXXXXXXXXX",
    "HR & Personalentwicklung" : "XXXXXXXX-6074-XXXX-XXXX-XXXXXXXXXXXX",
    "Private Vermögens- und Finanzberatung" : "XXXXXXXX-b09c-XXXX-XXXX-XXXXXXXXXXXX",
    "Produkt & Marken-Management" : "XXXXXXXX-68cd-XXXX-XXXX-XXXXXXXXXXXX",
    "Revision" : "XXXXXXXX-aaf4-XXXX-XXXX-XXXXXXXXXXXX",
}


# path to "data" directory in which the df are (going to be) saved
SCRIPT_PATH = os.path.dirname( __file__ )
DATA_DIR = os.path.join( SCRIPT_PATH, '..', 'data')

if not os.path.exists(DATA_DIR):
        os.mkdir(DATA_DIR)

TARGET_DIR = f"{DATA_DIR}/user_group-organisation_from_parent_Bank"

# user groups / organisations level 2
df1 = gqlix.get_user_groups_by_hierarchy_level(level= "2")
gqlix.save_df_as_csv(df1, target_file="all_level_2_user_groups-organisations", target_dir=TARGET_DIR)

# user group level 2, parent = Bank
df1 = gqlix.get_user_groups_by_hierarchy_level(level= "2" , relation_to_parent=True, parent_leanix_id = user_groups_dict["BANK"])
gqlix.save_df_as_csv(df1, target_file="user_group-organisation_level_2_Parent_Bank", target_dir=TARGET_DIR)

df_ls = []

# user group level 3, parent = Bank / ...
# Example: user group level 3, parent = Bank / IT & Services / ...
for user_group, id in user_groups_dict.items():
    #print(user_group, ":", id)
    if user_group != "BANK":
        # get data frames
        _level = 3
        df = gqlix.get_user_groups_by_hierarchy_level(level= _level , relation_to_parent= True, parent_leanix_id= id)
        df["parent"] = user_group
        df["parent_level"] = _level - 1 
        
        if df.empty:
            # if parent has no childern (Untergruppen), i.e. df is empty
            gqlix.save_df_as_csv(df= df, target_file= f"EMPTY!-user_group-organisation_level_level_3_from_parent_{user_group}", target_dir= TARGET_DIR) 
        else:    
            # save data frames as csv files
            gqlix.save_df_as_csv(df= df, target_file= f"user_group-organisation_level_level_3_from_parent_{user_group}", target_dir= TARGET_DIR)
            df["displayName"] = df["displayName"].apply(lambda row : str(row).removeprefix(f"Bank / {user_group} / "))
            df_ls.append(df)

# create empty df to host data from all dfs in df_ls
user_groups_df = pd.DataFrame(columns= ["displayName", "id", "level", "parent", "parent_level", "level_1"])
user_groups_df = pd.concat(df_ls, ignore_index= True)
user_groups_df["level_1"] = "Bank"

# save user_groups_df as csv files
gqlix.save_df_as_csv(df= user_groups_df, target_file= f"all_user_groups-organisations_from_parent_Bank", target_dir= TARGET_DIR)

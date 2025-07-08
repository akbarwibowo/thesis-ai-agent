from utils.databases import influxdb, mongodb
from utils.narrative_data_getter import narrative_module
from utils.token_data_getter import token_selection, technical_data_module, fundamental_data_module
from utils.technical_calculator import indicator_module


if __name__ == "__main__":
    # narrative_data = narrative_module.get_narrative_data(
    #     twitter_scrape_max_tweets=100,
    #     cointelegraph_max_articles=100,
    # )

    # if narrative_data:
    #     save_narrative_to_db = narrative_module.save_narrative_data_to_db(narrative_data=narrative_data)
    #     if save_narrative_to_db:
    #         print("Narrative data saved successfully.")
    #     else:
    #         print("Failed to save narrative data.")
    # else:
    #     print("No narrative data found.")

    collection_name = narrative_module.collection_name
    second_retrieve_narrative = mongodb.retrieve_documents(collection_name)

    if second_retrieve_narrative:
        print(f"Retrieved {len(second_retrieve_narrative)} narrative documents from the database.")
    else:
        print("No narrative documents found in the database.")
    
    categories_and_tokens_selected = token_selection.categories_selector(categories=['ai agent', 'layer 1', 'memecoin'])

    if categories_and_tokens_selected:
        print(f'Categories and tokens selected: {categories_and_tokens_selected}')
    else:
        print("No categories or tokens selected.")

    tokens_id = []

    for category in categories_and_tokens_selected:
        tokens_id.extend(category.get('tokens', []))

    fa_data = fundamental_data_module.get_fundamental_data_of_tokens(tokens_id)
    if fa_data:
        print(f"Fundamental data retrieved for {len(fa_data)} tokens.")
        save_fa_to_db = fundamental_data_module.save_fundamental_data_to_db(fundamental_data=fa_data)
        if save_fa_to_db:
            print("Fundamental data saved successfully.")
        else:
            print("Failed to save fundamental data.")
    else:
        print("No fundamental data found.")
    ta_data = technical_data_module.get_price_data_of_tokens(tokens_id)
    if ta_data:
        print(f"Technical data retrieved for {len(ta_data)} tokens.")
        save_ta_to_db = technical_data_module.save_price_data_to_db(price_data=ta_data)
        if save_ta_to_db:
            print("Technical data saved successfully.")
        else:
            print("Failed to save technical data.")
    else:
        print("No technical data found.")
    


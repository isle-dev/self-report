import argparse
import csv
import random
import numpy as np
import pandas as pd

from src.prompt import DOMAINS, ROLES, OBJECTIVES, INFO


def generate_personal_profile(profile_save_path, sample_num=None, adj_num=None):
    adjectival_markers = pd.read_csv("data/adjectival_markers.csv")
    qualifier = 'extremely'

    # Categorize adjective words based on their domain
    adjectives = {}
    for index, row in adjectival_markers.iterrows():
        domain = row['Domain']
        if domain not in adjectives.keys():
            adjectives[domain] = {'low_marker': [row['Low Marker']], 'high_marker': [row['High Marker']]}
        else:
            adjectives[domain]['low_marker'].append(row['Low Marker'])
            adjectives[domain]['high_marker'].append(row['High Marker'])

    # Save generated profile
    with open(profile_save_path, 'w') as file:
        connector = ', ' + qualifier + ' '
        starter = qualifier + ' '
        csv_data = [['personal_profile', 'domain', 'level']]

        # Generate personal profiles with a specified number of adj words
        for domain, markers in adjectives.items():
            save_index = []
            while len(save_index) < sample_num:
                adj_index_list = random.sample(range(0, len(markers['low_marker'])), adj_num)
                low_adj_list = np.take(markers['low_marker'], adj_index_list)
                high_adj_list = np.take(markers['high_marker'], adj_index_list)
                if adj_index_list not in save_index:
                    low_profile = starter + connector.join(low_adj_list[:-1]) + ' and {} {}\n'.format(qualifier, low_adj_list[-1])
                    high_profile = starter + connector.join(high_adj_list[:-1]) + ' and {} {}\n'.format(qualifier, high_adj_list[-1])

                    save_index.append(adj_index_list)

                    csv_data.append([low_profile, domain, "Low"])
                    csv_data.append([high_profile, domain, "High"])

        writer = csv.writer(file)
        writer.writerows(csv_data)


def generate_prompt(role, objectives, personal_info, additional_info):
    profile = personal_info['personal_profile'].strip()
    domain = DOMAINS[personal_info['domain']]
    level = personal_info['level'].lower()

    prompt = (f"You are {role} simulating a personality with a {level} level of {domain}. "
              f"Shape your responses using these key adjectives: you are {profile}.\n"
              f"Your main objective is to {objectives}. {additional_info}\n"
              f"The personality with a {level} level of {domain} and the key adjectives should guide your questions and responses.")
    return prompt


def generate_incontext_prompt(task_type, profile_save_path):
    profile_df = pd.read_csv(profile_save_path)

    role = ROLES[task_type]
    objectives = OBJECTIVES[task_type]
    additional_info = INFO[task_type]

    prompt_list = []
    for index, profile in profile_df.iterrows():
        final_prompt = generate_prompt(role, objectives, profile, additional_info)
        prompt_list.append(final_prompt)
    profile_df['personal_profile'] = prompt_list
    profile_file_name = profile_save_path.split('.')[0]
    profile_df.to_csv(f"{profile_file_name}_{task_type}.csv",index=False)


if __name__ == "__main__":
    argparser = argparse.ArgumentParser()
    argparser.add_argument('--profile_save_path', type=str, default='data/personal_profile.csv')
    argparser.add_argument('--task_type', type=str, default='social', choices=['social', 'job', 'public', 'travel', 'inquiry'])

    args = argparser.parse_args()

    generate_incontext_prompt(args.task_type, args.profile_save_path)
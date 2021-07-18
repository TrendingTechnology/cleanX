# -*- coding: utf-8 -*-
"""
clean X : Library for cleaning radiological data used in machine learning
applications
module csv_processing: processing of csvs related to images
"""

import pandas as pd


class MLSetup:
    """
    This class allows configuration of the train and test datasets
    organized into a pandas dataframe
    to be checked for problems, and creates reports, which can be
    put in multiple output options.
    """
    def __init__(self, train_df, test_df):
        # TODO: Implement
        self.train_df = train_df
        self.test_df = test_df
        
    # def train_maker():

    def metadata(self):
        return self.train_df.columns, self.test_df.columns
    
    def concat_dataframe(self):
        return self.train_df.concatenate(self.test_df)
    
    def duplicated(self):
        return self.concat_dataframe().duplicated()


# to run on dataframes
def check_paths_for_group_leakage(train_df, test_df, unique_id):
    """
    Finds train samples that have been accidentally leaked into test
    samples

    :param train_df: Pandas :code:`DataFrame` containing information about
                     train assets.
    :type train_df: :pd:`DataFrame`
    :param test_df: Pandas :code:`DataFrame` containing information about
                    train assets.
    :type test_df: :pd:`DataFrame`

    :return: duplications of any image into both sets as a new
             :code:`DataFrame`
    :rtype: :pd:`DataFrame`
    """
    pics_in_both_groups = train_df.merge(test_df, on=unique_id, how='inner')
    return pics_in_both_groups


def see_part_potential_bias(df, label, sensitive_column_list):
    """
    This function gives you a tabulated :code:`DataFrame` of sensitive columns
    e.g. gender, race, or whichever you think are relevant,
    in terms of a labels (put in the label column name).
    You may discover all your pathologically labeled sample are of one ethnic
    group, gender or other category in your :code:`DataFrame`. Remember some
    early neural nets for chest X-rays were less accurate in women and the
    fact that there were fewer X-rays of women in the datasets they built on
    did not help

    :param df: :code:`DataFrame` including sample IDs, labels, and sensitive
               columns
    :type df: :pd:`DataFrame`
    :param label: The name of the column with the labels
    :type label: string
    :param sensitive_column_list: List names sensitive columns on
                                  :code:`DataFrame`
    :type sensitive_column_list: list

    :return: tab_fight_bias2, a neatly sorted :code:`DataFrame`
    :rtype: :pd:`DataFrame`
    """

    label_and_sensitive = [label]+sensitive_column_list
    tab_fight_bias = pd.DataFrame(
        df[label_and_sensitive].value_counts()
    )
    tab_fight_bias2 = tab_fight_bias.groupby(label_and_sensitive).sum()
    tab_fight_bias2 = tab_fight_bias2.rename(columns={0: 'sums'})
    return tab_fight_bias2


def understand_df(df):
    """
    Takes a :code:`DataFrame` (if you have a :code:`DataFrame` for images)
    and prints information including length, data types, nulls and number
    of duplicated rows

    :param df: :code:`DataFrame` you are interested in getting features of.
    :type df: :pd:`DataFrame`

    :return: Prints out information on :code:`DataFrame`.
    :rtype: NoneType
    """
    print("The DataFrame has", len(df.columns), "columns, named", df.columns)
    print("")
    print("The DataFrame has", len(df), "rows")
    print("")
    print("The types of data:\n", df.dtypes)
    print("")
    print("In terms of nulls, the DataFrame has: \n", df[df.isnull()].count())
    print("")
    print(
        "Number of duplicated rows in the data is ",
        df.duplicated().sum(),
        ".",
    )
    print("")
    print("Numeric qualities of numeric data: \n", df.describe())


def show_duplicates(df):
    """
    Takes a :code:`DataFrame` (if you have a :code:`DataFrame` for images)
    and prints duplicated rows
    """
    if df.duplicated().any():
        print(
            "This DataFrame table has",
            df.duplicated().sum(),
            " duplicated rows"
        )
        print("They are: \n", df[df.duplicated()])
    else:
        print("There are no duplicated rows")

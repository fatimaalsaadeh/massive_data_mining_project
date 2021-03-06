# -*- coding: utf-8 -*-
"""RecommendationSystemnm941.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/12FztYhC-Dq_WB-xFYSxtjl4OzVsMpTGX

# CS 550 - Massive Data Mining 
# Recommendation Systems
## Team Members
### 1. Rushabh Bid ()
### 2. Fatima AlSaadeh ()
### 3. Keya Desai ()
### 4. Naveen Narayanan Meyyappan (nm941)

#### Data set: Movie review data set from "https://grouplens.org/datasets/movielens/latest/"

## Data selection and preprocessing
"""

# Installing the required packages
pip install surprise

# Importing the required libraries
from surprise import Reader, Dataset
from surprise import SVD, accuracy, SVDpp, SlopeOne, BaselineOnly, CoClustering
import datetime
import requests, zipfile, io
from os import path
import pandas as pd
import tqdm as tqdm
from numpy import *
from sklearn.model_selection import train_test_split 
from collections import defaultdict
import time
import warnings
warnings.filterwarnings("ignore")

# Reading the data 
rating_data = {}
movie_data = {}
training_data = []
testing_data = []
mapping_data = []
unique_user_id = []

# download http://files.grouplens.org/datasets/movielens/ml-latest-small.zip with 1M records File
# all files should be placed inside ml-latest folder
if not path.exists('ml-latest-small'):
    print("Downloading Files for first time use: ")
    download_file = requests.get('http://files.grouplens.org/datasets/movielens/ml-latest-small.zip')
    zipped_file = zipfile.ZipFile(io.BytesIO(download_file.content)) # having First.csv zipped file.
    zipped_file.extractall()


# Loading the mapping data which is to map each movie Id
# in the ratings with it's title and genre
# the resulted data structure is a dictionary where the
# movie id is the key, the genre and titles are values
def load_mapping_data():
    chunk_size = 500000
    df_dtype = {
        "movieId": int,
        "title": str,
        "genres": str
    }
    cols = list(df_dtype.keys())
    for df_chunk in tqdm.tqdm(pd.read_csv('ml-latest-small/movies.csv', usecols=cols, dtype=df_dtype, chunksize=chunk_size)):
        df_chunk.shape[0]
        combine_data = [list(a) for a in
                        zip(df_chunk["movieId"].tolist(), df_chunk["title"].tolist(),
                            df_chunk["genres"].tolist())]
        for a in combine_data:
            movie_data[a[0]] = [a[1], a[2]]
    del df_chunk

# Loading the rating data which is around 27M records it takes around 2 minutes
# the resulted data structure us a dictionary where the
# user id is the key and all their raings are values for example for user 1 :
# 1 = {
#     [movieId,rating,timestamp],
#     [movieId,rating,timestamp],
#     [movieId,rating,timestamp],
#   }


def load_data():
    chunk_size = 50000
    df_dtype = {
        "userId": int,
        "movieId": int,
        "rating": float,
        "timestamp": int,
    }
    cols = list(df_dtype.keys())
    for df_chunk in tqdm.tqdm(pd.read_csv('ml-latest-small/ratings.csv', usecols=cols, dtype=df_dtype, chunksize=chunk_size)):
        user_id = df_chunk["userId"].tolist()
        unique_user_id.extend(set(user_id))
        movie_id = df_chunk["movieId"].tolist()
        rating = df_chunk["rating"].tolist()
        timestamp = df_chunk["timestamp"].tolist()
        combine_data = [list(a) for a in zip(user_id, movie_id, rating, timestamp)]
        for a in combine_data:
            if a[0] in rating_data.keys():
                rating_data[a[0]].extend([[a[0], a[1], a[2], a[3]]])
            else:
                rating_data[a[0]] = [[a[0], a[1], a[2], a[3]]]
    del df_chunk
    return(rating_data)

# Split the data into training and testing
# this processes isn't being done for the whole dataset instead it's being done
# for each user id, for each user we split their ratings 80 training and 20 testing
# the resulted training and testing datasets are including the whole original dataset

def spilt_data():
    t0 = time.time()
    t1 = time.time()
    for u in unique_user_id:
        if len(rating_data[u]) == 1:
            x_test = rating_data[u]
            x_train = rating_data[u]
        else:
            x_train, x_test = train_test_split(rating_data[u], test_size=0.2)
        training_data.extend(x_train)
        testing_data.extend(x_test)
    total = t1 - t0
    print(int(total))

def get_movie_title(movie_id):
    if movie_id in movie_data.keys():
        return movie_data[movie_id][0]

def get_movie_genre(movie_id):
    if movie_id in movie_data.keys():
        return movie_data[movie_id][1]

def convert_traintest_dataframe_forsurprise(training_dataframe, testing_dataframe):
    training_dataframe = training_dataframe.iloc[:, :-1]
    testing_dataframe = testing_dataframe.iloc[:, :-1]
    reader = Reader(rating_scale=(0,5))
    trainset = Dataset.load_from_df(training_dataframe[['userId', 'movieId', 'rating']], reader)
    testset = Dataset.load_from_df(testing_dataframe[['userId', 'movieId', 'rating']], reader)
    trainset = trainset.construct_trainset(trainset.raw_ratings)
    testset=testset.construct_testset(testset.raw_ratings)
    return([trainset,testset])

def baseline(trainset, testset):
    algo = BaselineOnly()
    algo.fit(trainset)
    print("Predictions")
    predictions = algo.test(testset)
    accuracy.rmse(predictions)
    accuracy.mae(predictions)
    return(predictions)

def svdalgorithm(trainset, testset):
    algo = SVD()
    algo.fit(trainset)
    print("Predictions")
    predictions = algo.test(testset)
    accuracy.rmse(predictions)
    accuracy.mae(predictions)
    return(predictions)

def movie_recommendation(predictions, n=10):
    # First map the predictions to each user.
    algorithmrecommendations_for_each_user = defaultdict(list)
    testdaterecommendations_for_each_user = defaultdict(list)
    # Creating a dictionary with user_id as the key and the movie_id and the estimated_rating as the value
    for user_id, movie_id, true_rating, estimated_rating, _ in predictions:
        algorithmrecommendations_for_each_user[user_id].append((movie_id, estimated_rating))
        testdaterecommendations_for_each_user[user_id].append((movie_id, true_rating))
    # Now we will sort the Estimated_rating of different movies for each user
    for user_id, user_ratings in algorithmrecommendations_for_each_user.items():
        user_ratings.sort(key=lambda x: x[1], reverse=True)
        # Filtering the values to top n
        algorithmrecommendations_for_each_user[user_id] = user_ratings[:n]
    # Now we will sort the True_rating of different movies for each user
    for user_id, user_ratings in testdaterecommendations_for_each_user.items():
        user_ratings.sort(key=lambda x: x[1], reverse=True)
        # Filtering the values to top n
        testdaterecommendations_for_each_user[user_id] = user_ratings[:n]
    return([algorithmrecommendations_for_each_user,testdaterecommendations_for_each_user])

def precision_recall_calculation(predictions, threshold=3.5):

    # First map the predictions to each user.
    user_predict_true = defaultdict(list)
    for user_id, movie_id, true_rating, predicted_rating, _ in predictions:
        user_predict_true[user_id].append((predicted_rating, true_rating))

    precisions = dict()
    recalls = dict()
    for user_id, user_ratings in user_predict_true.items():

        # Sort user ratings by estimated value
        user_ratings.sort(key=lambda x: x[0], reverse=True)

        # Number of relevant items
        no_of_relevant_items = sum((true_rating >= threshold) for (predicted_rating, true_rating) in user_ratings)

        # Number of recommended items in top 10
        no_of_recommended_items = sum((predicted_rating >= threshold) for (predicted_rating, true_rating) in user_ratings[:10])

        # Number of relevant and recommended items in top 10
        no_of_relevant_and_recommended_items = sum(((true_rating >= threshold) and (predicted_rating >= threshold)) for (predicted_rating, true_rating) in user_ratings[:10])

        # Precision: Proportion of recommended items that are relevant
        precisions[user_id] = no_of_relevant_and_recommended_items / no_of_recommended_items if no_of_recommended_items != 0 else 1

        # Recall: Proportion of relevant items that are recommended
        recalls[user_id] = no_of_relevant_and_recommended_items / no_of_relevant_items if no_of_relevant_items != 0 else 1

    # Averaging the values for all users
    average_precision=sum(precision for precision in precisions.values()) / len(precisions)
    average_recall=sum(recall for recall in recalls.values()) / len(recalls)
    F_score=(2*average_precision*average_recall) / (average_precision + average_recall)
    
    return [average_precision, average_recall, F_score]

if __name__ == "__main__":
    print("Data Loading and Processing, Estimated Time 2 minutes :")
    load_data()
    print("Training and Testing DataSets Construction, Estimated Time 40 seconds :")
    spilt_data()
    print("Mapping Data Processing :")
    load_mapping_data()
    print("Movie name with id = 1 :")
    print(get_movie_title(1))
    print("Movie genre with id = 1 :")
    print(get_movie_genre(1))
    training_dataframe=pd.DataFrame.from_records(training_data)
    training_dataframe.columns=["userId","movieId","rating","timestamp"]
    testing_dataframe=pd.DataFrame.from_records(testing_data)
    testing_dataframe.columns=["userId","movieId","rating","timestamp"]
    trainset,testset=convert_traintest_dataframe_forsurprise(training_dataframe,testing_dataframe)
    print("Baseline algorithm using surprise package")
    baseline(trainset, testset)
    print("SVD algorithm using surprise package")
    predictions=svdalgorithm(trainset,testset)
    algorithm_recommendations,testdata_recommendations = movie_recommendation(predictions, n=10)
    # Print the recommended movies for each user
    #for user_id, user_ratings in algorithm_recommendations.items():
    #  print(user_id, [movie_id for (movie_id, estimated_rating) in user_ratings])
    [precision, recall, F_score] = precision_recall_calculation(predictions, threshold=3.5)
    print("Precision=", precision)
    print("Recall=", recall)
    print("F-Score=",F_score)
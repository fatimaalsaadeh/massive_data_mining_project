import data
from collections import defaultdict
from itertools import combinations, product
import numpy as np
from scipy.stats import pearsonr

def generate_seq(df, users):
	# key:user val: (item, rating) in sorted order
	seq = defaultdict(list)
	# key:user val: list of ratings
	ratings = defaultdict(list)
	# key:user val: list of items rated
	items = defaultdict(list)
	# dict of dict with {key:user {key:item val: rating}}
	item_ratings = {}

	for u in users:
		df_u = df[df['userId'] == u]
		df_u = df_u.sort_values(by = ['timestamp'])
		items[u].append(df_u['movieId'].unique())
		item_ratings[u] = {}
		for index, row in df_u.iterrows():
			seq[u].append((row['movieId'], row['rating']))
			ratings[u].append(row['rating'])
			item_ratings[u][row['movieId']] = row['rating']

	return seq, ratings, items, item_ratings

def deviation_ratings(r_u, r_v, r_u_i, r_v_i):
	max_ru, min_ru, max_rv, min_rv = np.max(r_u), np.min(r_u), np.max(r_v), np.min(r_v)
	return np.abs((r_u_i - max_ru)/(max_ru - min_ru) - (r_v_i - max_rv)/(max_rv - min_rv))

def compute_lcsis(seq, users, ratings, items, theta = 0.2):

	# key: (user u,user v) val: |lcsis(u,v)|
	lcsis = {}
	# key: (user u,user v) val: no. of items rated by both u and v [used to calculate similarity]
	common_count = {}
	# key: (user u,user v) val: items rated by both u and v [used to calculate similarity]
	common_items = {}
	# key: (user u,user v) val: no. of items rated by u + no. of items rated by v [used to calculate similarity]
	total = {}
	for u, v in combinations(users, 2):
		m, n = len(seq[u]), len(seq[v])
		w = np.zeros((m+1, n+1))

		for i in range(m+1):
			for j in range(n+1):
				if(i ==0 or j==0):
					w[i][j] = 0
				else:
					dev = deviation_ratings(ratings[u], ratings[v], ratings[u][i-1], ratings[v][j-1])
					if(seq[u][i-1][0] == seq[v][j-1][0] and dev <= theta):
						w[i][j] = w[i-1][j-1] + 1
					else:
						w[i][j] = max(w[i,j-1], w[i-1,j])

		lcsis[(u,v)] = w[m][n]
		total[(u,v)] = m + n

		if(len(items[u][0])>len(items[v][0])):
			common_items[(u,v)] = list(set(items[u][0]).intersection(items[v][0]))
			common_count[(u,v)] = len(common_items[(u,v)])
		else:
			common_items[(u,v)] = list(set(items[v][0]).intersection(items[u][0]))
			common_count[(u,v)] = len(common_items[(u,v)])

	for u in users:
		lcsis[(u,u)] = len(seq[u])

	return lcsis, total, common_count, common_items

def compute_position(j, u, v, i, tupple_i, seq_v, ratings, theta):
	target_item = tupple_i[0]
	for x in range(1, j+1):
		if(seq_v[x-1][0] == target_item):
			dev = deviation_ratings(ratings[u], ratings[v], ratings[u][i-1], ratings[v][x-1])
			if(dev <= theta):
				return x
	return 0


def compute_acsis(seq, users, ratings, theta = 0.2):

	# key: (user u,user v) val: |acsis(u,v)|
	acsis = {}
	for u, v in combinations(users, 2):
		m, n = len(seq[u]), len(seq[v])
		w = np.zeros((m+1, n+1))

		for i in range(m+1):
			for j in range(n+1):
				if(i ==0 or j==0):
					w[i][j] = 1
				else:
					x = compute_position(j, u, v, i, seq[u][i-1], seq[v], ratings, theta)
					if(x == 0):
						w[i][j] = w[i-1][j]
					else:
						w[i][j] = w[i-1][j] + w[i-1][x-1]
		# print(np.sum(w))
		acsis[(u,v)] = w[m][n]

	for u in users:
		acsis[(u,u)] = 2^len(seq[u])
	return acsis

def similarity_is(lcsis, acsis, users, total, common, alpha = 0.5):
	sim = {}
	# key: (user u,user v) val: similarity based on interest sequence
	weighted_sim = {}
	for u,v in combinations(users, 2):
		if(u!=v):
			sim_lcsis = lcsis[(u,v)] / (np.sqrt(lcsis[(u,u)] * lcsis[(v,v)]))
			sim_acsis = acsis[(u,v)] / (np.sqrt(acsis[(u,u)] * acsis[(v,v)]))
			sim[(u,v)] = alpha * np.exp(sim_lcsis) + (1-alpha) * np.exp(sim_acsis)			 
			weighted_sim[(u,v)] = (sim[(u,v)] * common[(u,v)]) / total[(u,v)]

	return sim, weighted_sim

def similarity(weighted_sim, users, seq, common_items, item_ratings):

	# sim = {}
	# key: (user u,user v) val: similarity based on interest sequence * pearson correlaiton
	similarity_list = defaultdict(list)
	for u,v in combinations(users, 2):
		if(len(common_items[(u,v)])<=1):
			sim = 0
		else:
			common_rating_u = []
			common_rating_v = []

			for item in common_items[(u,v)]:
				common_rating_u.append(item_ratings[u][item])
				common_rating_v.append(item_ratings[v][item])

			corr,_ = pearsonr(common_rating_u, common_rating_v)
			if(np.isnan(corr)):
				sim = 0
			else:
			# sim[(u,v)] = corr * weighted_sim[(u,v)]
				sim = corr * weighted_sim[(u,v)]
		similarity_list[u].append((v, sim))
		similarity_list[v].append((u, sim))

	return similarity_list

def predict(u, i, similarity_list, K, ratings, item_ratings):
	r_hat = np.mean(ratings[u]) 
	top_k = sorted(similarity_list[u], key = lambda x:x[1], reverse=True)[:K]

	num = 0 
	deno = 0
	for t in top_k:
		v = t[0]
		sim = t[1]

		# if user v has rated item i
		if(i in item_ratings[v]):
			num += sim * (item_ratings[v][i] - np.mean(ratings[v]))
			deno += sim
	
	if(deno != 0):	
		r_hat += num/deno

	return r_hat



if __name__ == "__main__":
	df_train, df_test = data.get_train_test_data()
	# print(len(df_train['movieId'].unique()))

	df_subset = df_train[:250]
	# print(df_subset)
	users = df_subset['userId'].unique()

	seq, ratings, items, item_ratings = generate_seq(df_subset, users)
	# print(item_ratings[1][1210])

	print("In lcsis")
	lcsis, total, common_count, common_items = compute_lcsis(seq, users, ratings, items)

	print("In acsis")
	acsis = compute_acsis(seq, users, ratings)

	print("In sim")
	sim_is, weighted_sim = similarity_is(lcsis, acsis, users, total, common_count)
	similarity_list = similarity(weighted_sim, users, seq, common_items, item_ratings)

	print("Prediction")
	user = 1
	item = 1
	r = predict(user, item, similarity_list, K = 1, ratings, item_ratings)
	print(r)


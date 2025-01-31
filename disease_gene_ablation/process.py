#!/usr/bin/env python
# -*- coding: utf-8 -*-


import json
import pickle

import numpy as np
import torch
from torch import nn


def get_node_label():
    disease_set_path = "./data/disease_202/gwas_cui_MAPPED_TRAIT_threshold_30_tab.txt"
    with open(disease_set_path, 'r') as fin:
        lines = fin.readlines()

    # 获取每个node的set
    node_entrez = []
    node_disease = {}
    for disease_index, line in enumerate(lines):
        results = line.strip().split('\t')
        for node in results[2:]:
            if node in node_disease:
                node_disease[node].append(disease_index)
            else:
                node_disease[node] = [disease_index]
    print(len(node_disease))

    # 转化为node的label
    node_label = {}
    for node in node_disease:
        label = [0] * 202
        indexs = node_disease[node]
        for index in indexs:
            label[index] = 1
        node_label[node] = label
    return node_label


def get_node_feature(mode=None):
    if mode == "set2Gus":
        node_embed = np.load(
            '/data/nfsdata2/sunzijun/bio/9606v11&set2gau_entrez/set2Gau_src/output_embedg2g_node_emb.out.npy')
        with open('/data/nfsdata2/sunzijun/bio/9606v11&set2gau_entrez/set2Gau_src/map.json', 'r') as f:
            i2g, g2i = json.load(f)
        feature_dict = {}
        for i, node in enumerate(i2g.values()):
            feature_dict[node] = node_embed[i].tolist()
        print("entrez num:", len(feature_dict))
    elif mode == "pretrain":
        with open("./sub_data/emb.pk", "rb") as f:
            node_embed = pickle.load(f)
        with open("./sub_data/map.pk", "rb") as f:
            i2g, g2i = pickle.load(f)
        feature_dict = {}
        for i, node in enumerate(g2i.keys()):
            feature_dict[str(node)] = node_embed[i]
        print("entrez num:", len(feature_dict))
    else:
        feature_path = "/data/nfsdata2/sunzijun/bio/graph_feature/feature_100.json"
        with open(feature_path, 'r') as f:
            feature_data = json.load(f)
        feature_dict = {}
        for data in feature_data['data']:
            feature_dict[data['entrez_id']] = data['feature']
        print("entrez num:", len(feature_dict))
    return feature_dict


def get_network():
    # 构造图
    with open("./sub_data/network.pk", "rb") as f:
        network = pickle.load(f)

    # 添加node feature
    feature_dict = get_node_feature(mode='pretrain')
    with open("./sub_data/map.pk", "rb") as f:
        i2g, g2i = pickle.load(f)

    entrezs = [value for value in i2g.values()]
    feature_list = []
    init_num = 0
    for ent in entrezs:
        if ent in feature_dict:
            feature_list.append(feature_dict[ent])
        else:
            init_num += 1
            feature = nn.init.kaiming_normal_(torch.empty(1, 100))
            feature_list.append(feature.tolist()[0])
    print(init_num / len(entrezs), " node are initialized.")

    # network.ndata['feat'] = torch.randn((18547, 100))
    features = torch.FloatTensor(feature_list)
    network.ndata['feat'] = features

    # 添加node label
    not_in_num = 0
    in_num = 0
    node_label = get_node_label()
    node_label_list = []
    for ent in entrezs:
        if ent in node_label:
            in_num += 1
            node_label_list.append(node_label[ent])
        else:
            not_in_num += 1
            node_label_list.append([0] * 202)
    print(in_num, "/", len(node_label), " label node used")
    print(not_in_num, " not in node label")
    labels = torch.FloatTensor(node_label_list)
    network.ndata['label'] = labels

    # 构造train val test的mask
    train_mask = torch.bernoulli(torch.full([labels.shape[0]], 0.7)).bool()
    # val_mask = ~train_mask
    # test_mask = ~train_mask
    val_mask = torch.bernoulli(torch.full([labels.shape[0]], 1)).bool()
    test_mask = torch.bernoulli(torch.full([labels.shape[0]], 1)).bool()

    network.ndata['train_mask'] = train_mask
    network.ndata['val_mask'] = val_mask
    network.ndata['test_mask'] = test_mask

    # 返回构造的网络
    print(network)
    return network


if __name__ == '__main__':
    # get_node_feature(mode='deepwalk')
    get_network()
    get_node_label()

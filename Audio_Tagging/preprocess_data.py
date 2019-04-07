import os
from dataloader import get_verified_files_dict, get_unverified_files_dict, get_label_mapping
import numpy as np
np.random.seed(101)
from collections import Counter


def divide_chunks(l, n):
    for i in range(0, len(l), n):
        yield l[i:i + n]

def split_train_val():
    """
    Creates train/validation splits for
    :return:
    """
    splits = [[1, 2, 3], [2, 3, 4], [1, 2, 4], [1, 3, 4]]
    eval = [4,1,3,2]
    for i, split in enumerate(splits):
        with open('../datasets/cv/fold{}_train'.format(i + 1), 'w') as train_out:
            for fold in split:
                with open('../datasets/cv/fold{}'.format(fold), 'r') as in_file:
                    files = in_file.read()
                train_out.write(files)
        with open('../datasets/cv/fold{}'.format(eval[i]), 'r') as val_in:
            val_files = val_in.read()
        with open('../datasets/cv/fold{}_eval'.format(eval[i]), 'w') as val_out:
            val_out.write(val_files)


def create_stratified_cv_splits():
    """
    Creates a stratified cross-validation setup and stores a list of files for each fold
    :return:
    """
    files_curated_dict = get_verified_files_dict()
    files_noisy_dict = get_unverified_files_dict()

    curated_file_dict = {f:l for f,l in zip(files_curated_dict.keys(), files_curated_dict.values())}
    noisy_file_dict = {f:l for f,l in zip(files_noisy_dict.keys(), files_noisy_dict.values())}

    print('Number of curated labels: ', len(curated_file_dict))
    print('Number of noisy labels: ', len(noisy_file_dict))

    curated_label_dict = {}
    for file, labels in curated_file_dict.items():
        #if len(labels) > 1:
        #    for l in labels:
        #        if not l in curated_label_dict.keys():
        #            curated_label_dict[l] = [file]
        #        else:
        #            curated_label_dict[l].append(file)
        #else:
        label = labels[0]
        if not label in curated_label_dict.keys():
            curated_label_dict[label] = [file]
        else:
            curated_label_dict[label].append(file)

    noisy_label_dict = {}
    for file, labels in noisy_file_dict.items():
        #if len(labels) > 1:
        #    for l in labels:
        #        if not l in noisy_label_dict.keys():
        #            noisy_label_dict[l] = [file]
        #        else:
        #            noisy_label_dict[l].append(file)
        #else:
        label = labels[0]
        if not label in noisy_label_dict.keys():
            noisy_label_dict[label] = [file]
        else:
            noisy_label_dict[label].append(file)

    labels = list(curated_label_dict.keys())
    # randomly shuffle curated and noisy labels
    overall_dict = {}
    for l in labels:
        overall_dict[l] = curated_label_dict[l]
        overall_dict[l].extend(noisy_label_dict[l])
        np.random.shuffle(overall_dict[l])
        print("{} Samples for class {} in dictionary".format(len(overall_dict[l]), l))

    if not os.path.exists('../datasets/cv'):
        os.makedirs('../datasets/cv')

    try:
        fold1 = open('../datasets/cv/fold1', 'w')
        fold2 = open('../datasets/cv/fold2', 'w')
        fold3 = open('../datasets/cv/fold3', 'w')
        fold4 = open('../datasets/cv/fold4', 'w')
    except:
        print('Could not create cv files!')

    folds = [fold1, fold2, fold3, fold4]
    for l in labels:
        length = int(len(overall_dict[l])/4)+1
        chunks = list(divide_chunks(overall_dict[l], length))
        for chunk, fold in enumerate(folds):
            for file in chunks[chunk]:
                fold.write(file.replace('.wav', '') + '\n')

    split_train_val()

def main():
    create_stratified_cv_splits()

if __name__ == '__main__':
    main()
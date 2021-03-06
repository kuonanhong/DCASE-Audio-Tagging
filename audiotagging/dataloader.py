from scipy.io import wavfile
import tqdm
import numpy as np
np.random.seed(101)
import os

def repeat_spectrogram(spec, fixed_length):
    if spec.shape[1] < fixed_length:
        while spec.shape[1] < fixed_length:
            spec = np.concatenate((spec, spec), axis=-1)

    if spec.shape[1] > fixed_length:
        spec = spec[:, :fixed_length]

    return spec


def divide_chunks(spec, frame_length, jump):
    # Divide whole spectrogram into windows which overlap according to the jump parameter
    if jump != 0:
        for j in range(0, spec.shape[1]-jump, jump):
            yield spec[:, j:j + frame_length]
    else:
        for j in range(0, spec.shape[1], frame_length):
            yield spec[:, j:j + frame_length]

def sample_from_spec(spec, frame_size, feature_width):
    # sample frames of spectrogram randomly across the whole spectrogram
    frame_range = np.arange(0,spec.shape[1]-frame_size)
    start_idxs = np.random.choice(frame_range, feature_width)
    for idx in start_idxs:
        yield spec[:, idx:idx+frame_size]

def get_verified_files_dict(path='../datasets/'):
    with open(os.path.join(path, 'train_curated.csv'), 'r') as in_file:
        data_config = in_file.readlines()
        data_config = data_config[1:]

    verified_files_dict = {line.split(',')[0]: line[line.index(',')+1:].rstrip().replace('"', '').split(',')
                           for line in data_config}

    return verified_files_dict

def get_unverified_files_dict(path='../datasets/'):
    with open(os.path.join(path, 'train_noisy.csv'), 'r') as in_file:
        data_config = in_file.readlines()
        data_config = data_config[1:]

    unverified_files_dict = {line.split(',')[0]: line[line.index(',')+1:].rstrip().replace('"', '').split(',')
                             for line in data_config}

    return unverified_files_dict

def get_total_file_dict(path='../datasets/'):
    curated_files = get_verified_files_dict(path)
    noisy_files = get_unverified_files_dict(path)
    return dict(curated_files, **noisy_files)

def get_test_files_list():
    """
    Determines the ground-truth label of test audio samples.
    Returns
    -------
    test_files : dictionary
        List containing the name of an audio sample
    """
    test_files = os.listdir('../datasets/test')

    return test_files


def load_test_features(filelist, features, path='../features/',
                        fixed_length=3132, feature_width=348, jump=74):
    """
    Loads and returns test audio files.
    Parameters
    ----------
    filelist : List
        List containing names of relevant test files as strings.
    features : String
        String containing name of feature that should be loaded.
    path : String
        Path pointing to respective feature-folder.
    fixed_length : int
        Integer that restricts the final length of all features.
        Defaults to `3132`.
    feature_width : int
        Number of frames within a feature. Defaults to `9`.
    Returns
    -------
    test_files : List of Tuples
        List containing (data, label) tupels for all test audio clips.
    """
    X = []
    for file in filelist:
        data = np.load('{}/test/{}.npy'.format(os.path.join(path, features), file.rstrip().replace('.wav', '')))

        if features != 'mfcc':
            if data.shape[1] < fixed_length:
                # repeat spectrogram and split into frames
                data = repeat_spectrogram(data, fixed_length=fixed_length)
                data = list(divide_chunks(data, feature_width, jump))
            else:
                # spectrogram is too long - sample frames from spectrogram
                data = data[:, :fixed_length]
                data = list(divide_chunks(data, feature_width, jump))

        X.extend(np.asarray(data))

    return np.asarray(X)

def unison_shuffled_copies(a, b):
    assert len(a) == len(b)
    p = np.random.permutation(len(a))
    return a[p], b[p]

def load_features(filelist, features, num_classes, feature_path='../features/',
                    data_path='../datasets/', fixed_length=2784, feature_width=348, jump=174):
    """
    Loads and returns audio features and their respective labels.
    Parameters
    ----------
    filelist : List
        List containing names of relevant files as strings.
    features : String
        String containing name of feature that should be loaded.
    num_classes : int
        Number of possible labels.
    feature_path : String
        Path pointing to respective feature-folder.
    data_path : String
        Path pointing to `train_curated.csv` and `train_noisy.csv`.
    fixed_length : int
        Integer that restricts the final length of all features.
        Defaults to `3132`.
    feature_width : int
        Number of frames within a feature. Defaults to `9`.
    Returns
    -------
    X : Array
        Array containing loaded features for all files in filelist.
    y : Array
        Array containing labels for all files in filelist.
    """
    # load verified audio clips
    curated_files_dict = get_verified_files_dict(data_path)
    noisy_files_dict = get_unverified_files_dict(data_path)
    label_mapping, inv_label_mapping = get_label_mapping(data_path)
    X = []
    y = []

    for file in filelist:
        file = file.rstrip()+'.wav'
        if file in curated_files_dict.keys():
            data = np.load(
                '{}/train_curated/{}.npy'.format(os.path.join(feature_path, features), file.rstrip().replace('.wav', '')))

            labels = curated_files_dict[file]
        else:
            data = np.load(
                '{}/train_noisy/{}.npy'.format(os.path.join(feature_path, features), file.rstrip().replace('.wav', '')))

            labels = noisy_files_dict[file]

        if (data == None).any() or np.isnan(data).any():
            continue

        if features != 'mfcc':
            if data.shape[1] < fixed_length:
                # repeat spectrogram and split into frames
                data = repeat_spectrogram(data, fixed_length=fixed_length)
                data = list(divide_chunks(data, feature_width, jump))
            else:
                #spectrogram is too long - cut it to fixed length
                data = data[:, :fixed_length]
                data = list(divide_chunks(data, feature_width, jump))

        if len(labels) > 1:
            label = [label_mapping[l] for l in labels]
        else:
            label = label_mapping[labels[0]]

        label = one_hot_encode(np.asarray(label), num_classes)
        for i in range(len(data)):
            y.append(label)
        X.extend(np.asarray(data))

    return np.asarray(X), np.asarray(y)

def mixup_augmentation(X, y,  alpha=0.3):

    batch_size, h, w, c = X.shape
    l = np.random.beta(alpha, alpha, batch_size)
    X_l = l.reshape(batch_size, 1, 1, 1)
    y_l = l.reshape(batch_size, 1)

    # mix observations
    X1, X2 = X[:], X[::-1]
    X = X1 * X_l + X2 * (1.0 - X_l)
    one_hot = y

    # mix labels
    y1 = one_hot[:]
    y2 = one_hot[::-1]
    y = y1 * y_l + y2 * (1.0 - y_l)

    return X.astype(np.float32), y.astype(np.float32)

def concat_mixup_augmentation(X, y, alpha=0.3, p=0.5):

    batch_size, h, w, c = X.shape
    if np.random.random() < p:
        l = np.random.beta(alpha, alpha, batch_size)
        y_l = l.reshape(batch_size, 1)

        # mix observations
        X1 = X[:]
        X2 = X[::-1]
        w1 = int(w * (1.0-alpha))
        X = np.concatenate((X1[:, :, :w1, :], X2[:,:,w1::,:]), axis=2)

        # mix labels
        one_hot = y
        y1 = one_hot[:]
        y2 = one_hot[::-1]
        y = y1 * y_l + y2 * (1.0 - y_l)

        return X.astype(np.float32), y.astype(np.float32)
    else:
        return X, y

def event_oversampling(X, feature_width=348):
    batch_size, h, w, c = X.shape
    X_new = np.zeros((batch_size, h, feature_width, c), dtype=np.float32)
    for i in range(batch_size):
        # compute frame sample probabilities
        sample_probs = X[i, :, :, :].mean(axis=(0,2))
        sample_probs -= sample_probs.min()
        sample_probs /= sample_probs.sum()

        # sample center frame
        center_frame = np.random.choice(range(X.shape[2]), p = sample_probs)

        # set sample window
        start = center_frame - feature_width // 2
        start = np.clip(start, 0, X.shape[2] - feature_width)
        stop = start + feature_width

        X_new[i] = X[i, :, :, start:stop]

        return X_new

def frequency_masking(X, mf, F=27, v=128):

    X_new = []
    for x in X:
        f = np.random.uniform(low=0, high=F, size=mf).astype(np.int)
        diff = np.full(f.shape, (v-f))
        f0 = [np.random.choice(np.arange(d)).astype(np.int) for d in diff]

        for start, end in zip(f0, f):
            x[start:start+end,:,:] = 0.0
        X_new.append(x)

    return np.asarray(X_new)

def time_masking(X, mt, T=70, p=0.2):

    X_new = []
    for x in X:
        t = np.random.uniform(low=0, high=T, size=mt).astype(np.int)
        diff = np.full(t.shape, (x.shape[1]-t))
        t0 = [np.random.choice(np.arange(d)) for d in diff]

        for start, end in zip(t0, t):
            if end > p*x.shape[1]:
                end = x.shape[1]
            x[:,start:start+end, :] = 0.0
        X_new.append(x)

    return np.asarray(X)

def generate_in_background(generator, num_cached=10):
    """
    Runs a generator in a background thread, caching up to `num_cached` items.
    """
    try:
        from Queue import Queue
    except ImportError:
        from queue import Queue
    queue = Queue(maxsize=num_cached)
    sentinel = object()  # guaranteed unique reference

    # define producer (putting items into queue)
    def producer():
        for item in generator:
            queue.put(item)
        queue.put(sentinel)

    # start producer (in a background thread)
    import threading
    thread = threading.Thread(target=producer)
    thread.daemon = True
    thread.start()

    # run as consumer (read items from queue, in current thread)
    item = queue.get()
    while item is not sentinel:
        yield item
        item = queue.get()

def load_batches(filelist, batchsize, feature_path='../features/', data_path='../datasets/',
                 shuffle=False, drop_remainder=False, infinite=False, num_classes=80, features='mel', test=False,
                 augment=False, mixup=True, feature_width=348, fixed_length=2784, jump=174):
    num_datapoints = len(filelist)

    while True:

        if shuffle:
            np.random.shuffle(filelist)

        rest = (num_datapoints % batchsize)
        upper_bound = num_datapoints - (rest if drop_remainder else 0)
        for start_idx in range(0, upper_bound, batchsize):
            batch = filelist[start_idx: start_idx+batchsize]

            if not test:
                X, y = load_features(batch, features=features, num_classes=num_classes,
                                     feature_path=feature_path, data_path=data_path, fixed_length=fixed_length,
                                     feature_width=feature_width, jump=jump)
                X = X[:,:,:,np.newaxis]

                if mixup:
                    X, y = mixup_augmentation(X, y)

                if augment:
                    X_aug = frequency_masking(X, mf=2, v=X.shape[1])
                    X_aug = time_masking(X_aug, mt=2)
                    yield([X, X_aug], [y, y])
                    continue

                yield (X, y)
            else:
                X = load_test_features(batch, features, path=feature_path, feature_width=feature_width,
                                       fixed_length=fixed_length, jump=jump)
                X = X[:,:,:,np.newaxis]
                yield X

        if not infinite:
            break

def load_batches_verification(filelist, feature_path='../features/', data_path='../datasets/',
                 shuffle=False, drop_remainder=False, infinite=False, num_classes=80, features='mel', k=24, feature_width=348,
                    fixed_length=2784, jump=174):
    num_datapoints = len(filelist)

    while True:

        if shuffle:
            np.random.shuffle(filelist)

        rest = (num_datapoints % k)
        upper_bound = num_datapoints - (rest if drop_remainder else 0)
        for start_idx in range(0, upper_bound, k):
            X_train = []
            y_train = []
            for file in filelist[start_idx:start_idx+k]:

                X_temp, y_temp = load_features([file], features=features, num_classes=num_classes,
                                     feature_path=feature_path, data_path=data_path, fixed_length=fixed_length,
                                     feature_width=feature_width, jump=jump)

                if X_temp.shape[0] == 0:
                    continue

                rand_ind = np.random.choice(X_temp.shape[0])
                X_train.append(X_temp[rand_ind])
                y_train.append(y_temp[rand_ind])

            yield (np.asarray(X_train)[:,:,:,np.newaxis], np.asarray(y_train))

        if not infinite:
            break


def load_verified_files(features=None):
    verified_files_dict = get_verified_files_dict()

    # load verified audio clips
    verified_files = []
    for file, label in tqdm.tqdm(zip(verified_files_dict.keys(), verified_files_dict.values()), 'Loading verified clips'):
        if not features:
            _, data = wavfile.read('../datasets/train_curated/{}'.format(file))
        else:
            data = np.load('../features/{}/train_curated/{}.npy'.format(features, file.replace('wav', features)))

        verified_files.append((data, label))

    return verified_files

def load_unverified_files(features=None):
    unverified_files_dict = get_unverified_files_dict()

    # load verified audio clips
    unverified_files = []
    for file, label in tqdm.tqdm(zip(unverified_files_dict.keys(), unverified_files_dict.values()),
                                 'Loading verified clips'):
        if not features:
            _, data = wavfile.read('../datasets/train_curated/{}'.format(file))
        else:
            data = np.load('../features/{}/train_curated/{}.npy'.format(features, file.replace('wav', features)))

        unverified_files.append((data, label))

    return unverified_files

def get_label_mapping(path='../datasets/'):
    with open(os.path.join(path, 'train_curated.csv'), 'r') as in_file:
        train_list = in_file.readlines()

    train_list = train_list[1:]
    single_labels = []
    labels = [line[line.index(',')+1:].rstrip().replace('"', '').split(',')
                           for line in train_list]
    for label in labels:
        if len(label) > 1:
            single_labels.extend([l for l in label])
        else:
            single_labels.append(label[0])

    unique_labels = np.unique(single_labels)
    label_mapping = {label: index for index, label in enumerate(unique_labels)}
    inv_label_mapping = {v: k for k, v in zip(label_mapping.keys(), label_mapping.values())}
    return label_mapping, inv_label_mapping

def one_hot_encode(labels, num_classes):
    """
    Derives the one-hot-encoding representation of defined
    label for given number of classes.
    Parameters
    ----------
    labels : Array
        Array of indices to be one-hot-encoded.
    num_classes : int
        Total number of different classes.
    Returns
    -------
    encoding : Array
        Array containing one-hot-encoding, where all labels-th
        values are set to 1., and remaining values are 0.
    """
    encoding = np.zeros(shape=num_classes)
    encoding[labels] = 1
    return encoding
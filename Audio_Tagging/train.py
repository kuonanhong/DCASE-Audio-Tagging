import argparse
from dataloader import get_verified_files_dict, load_verified_files, get_label_mapping, one_hot_encode
import numpy as np
import os
import utils
import keras
from argparse import ArgumentParser
import config

parser = argparse.ArgumentParser()
parser.add_argument('-year', required=True)
parser.add_argument('-features', required=True)
parser.add_argument('-clf', help='Classifier to use, by default RF is used', default='RF')
args = parser.parse_args()

def opts_parser():
    descr = "Trains a neural network."
    parser = ArgumentParser(description=descr)
    parser.add_argument('modelfile', metavar='MODELFILE',
            type=str,
            help='File to save the learned weights to')
    config.prepare_argument_parser(parser)
    return parser

def save_model(modelfile, network, cfg):
    """
    Saves the learned weights to `filename`, and the corresponding
    configuration to ``os.path.splitext(filename)[0] + '.vars'``.
    """
    config.write_config_file(modelfile + '_auto.vars', cfg)
    network_yaml = network.to_yaml()
    with open(modelfile.replace('.py', ".yaml"), 'w') as yaml_file:
        yaml_file.write(network_yaml)

def main():
    label_mapping, inv_label_mapping = get_label_mapping(args.year)
    parser = opts_parser()
    options = parser.parse_args()
    modelfile = options.modelfile
    cfg = config.from_parsed_arguments(options)
    keras.backend.set_image_data_format('channels_first')

    print('Loading data...')
    data = load_verified_files(args.year, args.features)

    X = []
    y = []
    for x in data:
        label = x[1]
        x = x[0]
        for datapoint in x:
            X.append(datapoint)
            y.append(label_mapping[label])

    print('Load complete')
    X = np.asarray(X)
    y = np.asarray(y)

    print('Loading model')

    if not os.path.exists('models'):
        os.makedirs('models')

    if not os.path.exists('models/{}'.format(args.clf)):
        print('Modelfile does not exist')

    # import model from file
    selected_model = utils.import_model(modelfile)

    # instantiate neural network
    print("Preparing training function...")
    train_formats = (cfg['batch_size'], 1, X[0].shape[0], X[0].shape[1])
    network = selected_model.architecture(train_formats, cfg)

    # Add optimizer and compile model
    print("Compiling model ...")
    optimizer = keras.optimizers.Adam(lr=cfg['lr'])
    network.compile(optimizer=optimizer, loss=cfg["loss"], metrics=["acc"])

    print("Preserving architecture and configuration ..")
    save_model(modelfile.replace('.py', ''), network, cfg)

    # Add batch creator, and training procedure
    # For reproduction of CPJKU2018 we need to create their train/test split, and their training procedure

if __name__ == '__main__':
    main()

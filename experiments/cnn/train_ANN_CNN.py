import os
import pickle

import matplotlib.pyplot as plt
import numpy as np
import torch.nn as nn

from experiments.utils import Loss
from src.classifier import Classifier, weight_norm
from src.network import ConvNet
from src.utils import Dataset, get_dataset_loaders

try:
    import seaborn as sns
    plt.style.use('seaborn-paper')
except ImportError:
    pass

def run(save_loc="cnn/ANN", loss=Loss.CCE, activation=nn.ReLU):

    print("\n----- Running {} -----".format(os.path.basename(__file__)))

    ####################################################
    # Configure datasets.
    ####################################################

    dataset = Dataset.MNIST

    if dataset != Dataset.MNIST:
        save_loc += "_{}".format(str(dataset).split(".")[-1])

    batch_size_train = 64
    batch_size_test = 1000

    ####################################################
    # Configure Networks.
    ####################################################

    if loss==Loss.MSE:
        output = None
        loss_str = "mse"
    elif loss==Loss.CCE:
        output = lambda: nn.LogSoftmax(-1)
        loss_str = "nll"
    else:
        raise ValueError("Unrecognised loss :", loss)

    net_args = {
        'n_ch_conv': [32, 64],
        'kernel_size_conv': [5, 5],
        'n_in_fc': 1024,
        'n_hid_fc': [128],
        'activation_conv': [activation, activation],
        'activation_fc': activation,
        'dropout': lambda: nn.Dropout(0.4),
        'conv_args': {'stride': 1, 'padding': 0, 'bias': False},
        'pool_conv': lambda: nn.AvgPool2d(kernel_size=2, stride=2),
        'n_out': 10 if dataset != Dataset.EMNIST else 47,
        'bias_fc': False,
        'output': output
    }

    ####################################################
    # Train classifiers
    ####################################################

    n_seeds = 5

    losses = {}
    corrects = {}
    valid_scores = {}

    for i in range(n_seeds):
        lab = 'seed{}'.format(i)

        network = ConvNet(**net_args)

        train_loader, test_loader, validation_loader = get_dataset_loaders(
            dataset=dataset,
            train_batch=batch_size_train,
            test_batch=batch_size_test,
            unroll_img=False,
            max_value=1,
            get_validation=True)

        classifier = Classifier(network, train_loader, test_loader,
                                n_epochs=1 if dataset == Dataset.MNIST else 1,
                                learning_rate=5e-4,
                                init_weight_mean=0., init_weight_std=0.01, init_conv_weight_std=0.1,
                                loss=loss_str,
                                weight_range=None,
                                weight_normalisation=weight_norm.NONE,
                                log_interval=25, n_test_per_epoch=0,
                                save_path=os.path.join(save_loc, lab))

        train_losses, test_correct = classifier.train()

        losses[lab] = train_losses
        corrects[lab] = test_correct

        ####################################################
        # Validation
        ####################################################

        classifier.load(classifier.network_save_path)

        valid_loss, valid_correct = classifier.validate(validation_loader)

        print("Validation accuracy : {:.2f}%".format(100. * valid_correct / len(validation_loader.dataset)))
        valid_scores[lab] = 100. * valid_correct / len(validation_loader.dataset)

        validation_save_path = os.path.join(classifier.save_path, "validation_score.pkl")
        with open(validation_save_path, 'wb+') as output:
            pickle.dump(np.array([valid_loss, valid_correct]), output, pickle.HIGHEST_PROTOCOL)
            print('Validation scores saved to {}'.format(validation_save_path))

    print("Validation scores are:")
    for lab, score in valid_scores.items():
        print("\t{} : {:.2f}%".format(lab, score))

    ####################################################
    # Plot results
    ####################################################

    fig_fname = os.path.join(save_loc, "training_performance")

    with plt.style.context('seaborn-paper', after_reset=True):

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(7, 2.5), gridspec_kw={'wspace': 0.3})

        window = 25
        avg_mask = np.ones(window) / window

        for lab, data in losses.items():
            ax1.plot(np.convolve(data[:, 0], avg_mask, 'valid'),
                     np.convolve(data[:, 1], avg_mask, 'valid'),
                     label=lab, linewidth=0.75, alpha=0.8)
        ax1.legend()
        ax1.set_xlabel("Epoch")
        ax1.set_ylabel("Losses")

        for lab, data in corrects.items():
            ax2.plot(data[:, 0], data[:, 1] / len(test_loader.dataset), label=lab)
            print("{}: Best score {}/{}".format(lab, np.max(data), len(test_loader)))
        ax2.legend()
        ax2.set_xlabel("Epoch")
        ax2.set_ylabel("Accuracy")

        plt.savefig(fig_fname + ".png", bbox_inches='tight')
        plt.savefig(fig_fname + ".pdf", bbox_inches='tight')

if __name__ == "__main__":
    run()
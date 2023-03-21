# -*- coding: utf-8 -*-
"""ML2022Spring - HW1.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1FTcG6CE-HILnvFztEFKdauMlPKfQvm5Z

# **Homework 1: COVID-19 Cases Prediction (Regression)**

Objectives:
* Solve a regression problem with deep neural networks (DNN).
* Understand basic DNN training tips.
* Familiarize yourself with PyTorch.

If you have any questions, please contact the TAs via TA hours, NTU COOL, or email to mlta-2022-spring@googlegroups.com

# Download data
If the Google Drive links below do not work, you can download data from [Kaggle](https://www.kaggle.com/t/a3ebd5b5542f0f55e828d4f00de8e59a), and upload data manually to the workspace.
"""

# !gdown --id '1kLSW_-cW2Huj7bh84YTdimGBOJaODiOS' --output covid.train.csv
# !gdown --id '1iiI5qROrAhZn-o4FPqsE97bMzDEFvIdg' --output covid.test.csv

"""# Import packages"""

# Numerical Operations

# Reading/Writing Data

# For Progress Bar

# Pytorch

# For plotting learning curve

"""# Some Utility Functions

You do not need to modify this part.
"""




from torch.utils.tensorboard import SummaryWriter
from torch.utils.data import Dataset, DataLoader, random_split
import torch.nn as nn
import math
import numpy as np
import pandas as pd
import os
import csv
from tqdm import tqdm
import torch
def same_seed(seed):
    '''Fixes random number generator seeds for reproducibility.'''
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def train_valid_split(data_set, valid_ratio, seed):
    '''Split provided training data into training set and validation set'''
    valid_set_size = int(valid_ratio * len(data_set))
    train_set_size = len(data_set) - valid_set_size
    train_set, valid_set = random_split(data_set, [
                                        train_set_size, valid_set_size], generator=torch.Generator().manual_seed(seed))
    return np.array(train_set), np.array(valid_set)


def predict(test_loader, model, device):
    model.eval()  # Set your model to evaluation mode.
    preds = []
    for x in tqdm(test_loader):
        x = x.to(device)
        with torch.no_grad():
            pred = model(x)
            preds.append(pred.detach().cpu())
    preds = torch.cat(preds, dim=0).numpy()
    return preds


"""# Dataset"""


class COVID19Dataset(Dataset):
    '''
    x: Features.
    y: Targets, if none, do prediction.
    '''

    def __init__(self, x, y=None):
        if y is None:
            self.y = y
        else:
            self.y = torch.FloatTensor(y)

        self.x = torch.FloatTensor(x)
        # self.x = nn.functional.normalize(self.x, dim=1)

    def __getitem__(self, idx):
        if self.y is None:
            return self.x[idx]
        else:
            return self.x[idx], self.y[idx]

    def __len__(self):
        return len(self.x)


"""# Neural Network Model
Try out different model architectures by modifying the class below.
"""


class My_Model(nn.Module):
    def __init__(self, input_dim):
        super(My_Model, self).__init__()
        # TODO: modify model's structure, be aware of dimensions.
        self.layers = nn.Sequential(
            nn.Linear(input_dim, 32),
            nn.ReLU(),
            nn.Linear(32, 16),
            nn.ReLU(),
            nn.Linear(16, 8),
            nn.ReLU(),
            nn.Linear(8, 4),
            nn.ReLU(),
            nn.Linear(4, 2),
            nn.ReLU(),
            nn.Linear(2, 1)
        )

    def forward(self, x):
        x = self.layers(x)
        x = x.squeeze(1)  # (B, 1) -> (B)
        return x


"""# Feature Selection
Choose features you deem useful by modifying the function below.
"""


def select_feat(train_data, valid_data, test_data, select=None):
    '''Selects useful features to perform regression'''
    y_train, y_valid = train_data[:, -1], valid_data[:, -1]
    raw_x_train, raw_x_valid, raw_x_test = train_data[:,
                                                      :-1], valid_data[:, :-1], test_data

    if select is None:
        feat_idx = list(range(raw_x_train.shape[1]))
    else:
        feat_idx = select

    return raw_x_train[:, feat_idx], raw_x_valid[:, feat_idx], raw_x_test[:, feat_idx], y_train, y_valid


"""# Training Loop"""


def trainer(train_loader, valid_loader, model, config, device):

    # Define your loss function, do not modify this.
    criterion = nn.MSELoss(reduction='mean')

    # Define your optimization algorithm.
    # TODO: Please check https://pytorch.org/docs/stable/optim.html to get more available algorithms.
    # TODO: L2 regularization (optimizer(weight decay...) or implement by your self).
    # optimizer = torch.optim.SGD(
    #     model.parameters(), lr=config['learning_rate'], momentum=0.9)
    optimizer = torch.optim.Adam(model.parameters())
    scheduler = torch.optim.lr_scheduler.StepLR(
        optimizer, step_size=100, gamma=0.8)
    warmup_epoch = 100

    def schedule(epoch):
        if epoch <= warmup_epoch:
            prog = epoch / warmup_epoch
            return prog
        else:
            prog = (epoch - warmup_epoch) / (config["n_epochs"] - warmup_epoch)
            return 0.5 * (math.cos(prog * math.pi) + 1)
    scheduler = torch.optim.lr_scheduler.LambdaLR(
        optimizer, lr_lambda=schedule)

    writer = SummaryWriter()  # Writer of tensoboard.

    if not os.path.isdir('./models'):
        os.mkdir('./models')  # Create directory of saving models.

    n_epochs, best_loss, step, early_stop_count = config['n_epochs'], math.inf, 0, 0

    for epoch in range(n_epochs):
        model.train()  # Set your model to train mode.
        loss_record = []

        # tqdm is a package to visualize your training progress.
        train_pbar = tqdm(train_loader, position=0, leave=True)

        for x, y in train_pbar:
            optimizer.zero_grad()               # Set gradient to zero.
            x, y = x.to(device), y.to(device)   # Move your data to device.
            pred = model(x)
            loss = criterion(pred, y)
            # Compute gradient(backpropagation).
            loss.backward()
            optimizer.step()                    # Update parameters.
            step += 1
            loss_record.append(loss.detach().item())

            # Display current epoch number and loss on tqdm progress bar.
            train_pbar.set_description(f'Epoch [{epoch+1}/{n_epochs}]')
            train_pbar.set_postfix({'loss': loss.detach().item()})

        scheduler.step()
        mean_train_loss = sum(loss_record)/len(loss_record)

        writer.add_scalar('Loss/train', mean_train_loss, step)

        model.eval()  # Set your model to evaluation mode.
        loss_record = []
        for x, y in valid_loader:
            x, y = x.to(device), y.to(device)
            with torch.no_grad():
                pred = model(x)
                loss = criterion(pred, y)

            loss_record.append(loss.item())

        mean_valid_loss = sum(loss_record)/len(loss_record)
        print(
            f'Epoch [{epoch+1}/{n_epochs}]: Train loss: {mean_train_loss:.4f}, Valid loss: {mean_valid_loss:.4f}')
        writer.add_scalar('Loss/valid', mean_valid_loss, step)

        if mean_valid_loss < best_loss:
            best_loss = mean_valid_loss
            # Save your best model
            torch.save(model.state_dict(), config['save_path'])
            print('Saving model with loss {:.3f}...'.format(best_loss))
            early_stop_count = 0
        else:
            early_stop_count += 1

        if early_stop_count >= config['early_stop']:
            print('\nModel is not improving, so we halt the training session.')
            return


"""# Configurations
`config` contains hyper-parameters for training and the path to save your model.
"""

device = 'cuda' if torch.cuda.is_available() else 'cpu'
select = list(range(117))
with open("covid.train.csv", "r") as f:
    entris = f.readline().split(',')
remove = ["id", "anxious", "depressed", "worried_finances",
          "shop", "spent_time"]
remove += "CA,TX,NY,WA,AL,AK,AZ,AR,CO,CT,FL,GA,ID,IL,IN,IA,KS,KY,LA,MD,MA,MI,MN,MS,MO,NE,NV,NJ,NM,NC,OH,OK,OR,RI,SC,UT,VA".split(
    ',')
for i in remove:
    select.remove(entris.index(i))
config = {
    'seed': 19260817,      # Your seed number, you can pick your lucky number. :)
    'select': select,       # Whether to use all features.
    'valid_ratio': 0.2,   # validation_size = train_size * valid_ratio
    'n_epochs': 3000,     # Number of epochs.
    'batch_size': 128,
    'learning_rate': 1e-4,
    'betas': (0.9, 0.999),
    'weight_decay': 1e-4,
    # If model has not improved for this many consecutive epochs, stop training.
    'early_stop': 500,
    'save_path': './models/model.ckpt'  # Your model will be saved here.
}

"""# Dataloader
Read data from files and set up training, validation, and testing sets. You do not need to modify this part.
"""

# Set seed for reproducibility
same_seed(config['seed'])


# train_data size: 2699 x 118 (id + 37 states + 16 features x 5 days)
# test_data size: 1078 x 117 (without last day's positive rate)
train_data, test_data = pd.read_csv(
    './covid.train.csv').values, pd.read_csv('./covid.test.csv').values
train_data, valid_data = train_valid_split(
    train_data, config['valid_ratio'], config['seed'])

# Print out the data size.
print(f"""train_data size: {train_data.shape} 
valid_data size: {valid_data.shape} 
test_data size: {test_data.shape}""")

# Select features
x_train, x_valid, x_test, y_train, y_valid = select_feat(
    train_data, valid_data, test_data, config['select'])

# Print out the number of features.
print(f'number of features: {x_train.shape[1]}')

train_dataset, valid_dataset, test_dataset = COVID19Dataset(x_train, y_train), \
    COVID19Dataset(x_valid, y_valid), \
    COVID19Dataset(x_test)

# Pytorch data loader loads pytorch dataset into batches.
train_loader = DataLoader(
    train_dataset, batch_size=config['batch_size'], shuffle=True, pin_memory=True)
valid_loader = DataLoader(
    valid_dataset, batch_size=config['batch_size'], shuffle=True, pin_memory=True)
test_loader = DataLoader(
    test_dataset, batch_size=config['batch_size'], shuffle=False, pin_memory=True)

"""# Start training!"""

# put your model and data on the same computation device.
model = My_Model(input_dim=x_train.shape[1]).to(device)
trainer(train_loader, valid_loader, model, config, device)

"""# Plot learning curves with `tensorboard` (optional)

`tensorboard` is a tool that allows you to visualize your training progress.

If this block does not display your learning curve, please wait for few minutes, and re-run this block. It might take some time to load your logging information. 
"""

# Commented out IPython magic to ensure Python compatibility.
# %reload_ext tensorboard
# %tensorboard --logdir=./runs/

"""# Testing
The predictions of your model on testing set will be stored at `pred.csv`.
"""


def save_pred(preds, file):
    ''' Save predictions to specified file '''
    with open(file, 'w') as fp:
        writer = csv.writer(fp)
        writer.writerow(['id', 'tested_positive'])
        for i, p in enumerate(preds):
            writer.writerow([i, p])


model = My_Model(input_dim=x_train.shape[1]).to(device)
model.load_state_dict(torch.load(config['save_path']))
preds = predict(test_loader, model, device)
save_pred(preds, 'pred.csv')

"""# Reference
This notebook uses code written by Heng-Jui Chang @ NTUEE (https://github.com/ga642381/ML2021-Spring/blob/main/HW01/HW01.ipynb)
"""
'''
Created on Dec 21, 2016

@author: safdar
'''
import matplotlib
from sklearn.preprocessing.data import StandardScaler
from sklearn.cross_validation import train_test_split
from sklearn.svm.classes import LinearSVC
import time
from sklearn.utils import shuffle
matplotlib.use('TKAgg')
import matplotlib.image as mpimg
from extractors.spatialbinner import SpatialBinner
from extractors.hogextractor import HogExtractor
from extractors.colorhistogram import ColorHistogram
from extractors.featurecombiner import FeatureCombiner
import argparse
import numpy as np
import os
from sklearn.externals import joblib

CAR_FLAG = 1
NOTCAR_FLAG = 0

def getallpathsunder(path):
    if not os.path.isdir(path):
        raise "Folder {} does not exist, or is not a folder".format(path)
    cars = [os.path.join(dirpath, f)
            for dirpath, _, files in os.walk(path)
            for f in files if f.endswith('.png')]
    return cars

def appendXYs(imagefiles, extractor, label, Xs, Ys):
    print ("LABEL: {}".format(label))
    for idx, file in enumerate(imagefiles):
        image = mpimg.imread(file)
        Xs.append(extractor.extract(image))
        Ys.append(label)
        if idx % 100 == 0:
            print(".", end='', flush=True)
    print("")

if __name__ == '__main__':
    print ("###############################################")
    print ("#                   TRAINER                   #")
    print ("###############################################")

    parser = argparse.ArgumentParser(description='Object Classifier')
    parser.add_argument('-v', dest='vehicledir',    required=True, type=str, help='Path to folder containing vehicle images.')
    parser.add_argument('-n', dest='nonvehicledir',    required=True, type=str, help='Path to folder containing non-vehicle images.')
    parser.add_argument('-o', dest='output',   required=True, type=str, help='File to store trainer parameters for later use')
    parser.add_argument('-t', dest='testratio', default=0.10, type=float, help='% of training data held aside for testing.')
    parser.add_argument('-d', dest='dry', action='store_true', help='Dry run. Will not save anything to disk (default: false).')
    args = parser.parse_args()

    # Create all the extractors here:
    print ("Preparing feature extractors...")
    spatialex = SpatialBinner(color_space='RGB', size=(32,32))
    colorhistex = ColorHistogram(color_space='RGB', nbins=32, bins_range=(0, 256))
    hogex = HogExtractor(orientations=9, pixels_per_cell=8, cells_per_block=2)
    combiner = FeatureCombiner((spatialex, colorhistex, hogex))

    # Collect the image file names:
    print ("Gathering data...")
    cars = getallpathsunder(args.vehicledir)
    print ("Number of car images found: \t{}".format(len(cars)))
    assert len(cars)>0, "There should be at least one vehicle image to process. Found 0."
    notcars = getallpathsunder(args.nonvehicledir)
    print ("Number of non-car images found: \t{}".format(len(notcars)))
    assert len(notcars)>0, "There should be at least one non-vehicle image to process. Found 0."

    # Prepare feature vectors:
    print ("Extracting features...")
    Xs, Ys = [], []
    appendXYs(cars, combiner, CAR_FLAG, Xs, Ys)
    appendXYs(notcars, combiner, NOTCAR_FLAG, Xs, Ys)
    Xs = np.array(Xs, dtype=np.float64)
    print ("\tFeatures shape: {}".format(Xs.shape))

    # Prepare data:
    # - Normalize, shuffle and split:
    print ("Preparing data")
    X_scaler = StandardScaler().fit(Xs)
    scaled_Xs = X_scaler.transform(Xs)
    rand_state = np.random.randint(0, 100)
    scaled_Xs, Ys = shuffle(scaled_Xs, Ys, random_state=rand_state)
    X_train, X_test, Y_train, Y_test = train_test_split(scaled_Xs, Ys, test_size=args.testratio, random_state=rand_state)

    # If the SVM was not already trained:
    svc = None
    if not os.path.isfile(args.output):
        print ("Training the SVC...")
        svc = LinearSVC()
        t=time.time()
        svc.fit(X_train, Y_train)
        t2 = time.time()
        print(t2-t, 'Seconds to train SVC...')
    else:
        args.dry = True
        print ("SVC already trained. Reading from previous version.")
        svc = joblib.load(args.output)
        
    print('Train Accuracy of SVC = ', svc.score(X_train, Y_train))
    print('Test Accuracy of SVC = ', svc.score(X_test, Y_test))
    t=time.time()
    prediction = svc.predict(X_test[0].reshape(1, -1))
    t2 = time.time()
    print(t2-t, 'Seconds to predict with SVC')
    
    if not args.dry:
        print ("Saving checkpoints to file: {}".format(args.output))
        joblib.dump(svc, args.output)

    print ("Thank you. Come again!")

#!/usr/bin/python3.5
import pandas as pd


class ResultsFromAna:
    def __new__(cls, name, path=''):
        return pd.read_csv(path + name, skiprows=range(0, 7), names=["energy", \
                                                                     "trans_en", "trans_en_err", "channel",
                                                                     "channel_err",
                                                                     "counts", \
                                                                     "counts_err", "intensity", "intensity_err"], sep='\s+', dtype=float)


class Database():
    def __init__(self, lvlFileName, transitionsFileName):
        self.levels = pd.read_csv(lvlFileName, header=0, sep='\s+', keep_default_na=False)
        self.transitions = pd.read_csv(transitionsFileName, header=0, sep='\s+', keep_default_na=False)

    def slice(self, gamma_start_lvl, gamma_end_lvl):

        database_slice = self.transitions.loc[
            (self.transitions['from_lvl'] <= gamma_end_lvl) | (self.transitions['to_lvl'] >= gamma_start_lvl)]
        return database_slice




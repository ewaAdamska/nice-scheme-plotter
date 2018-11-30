# !/usr/bin/python3.5
import pandas as pd
from collections import OrderedDict


class Level():
    """This is class for excited nuclear levels, which contains all information
    about level itself and its plotting style.

    Parameters
    ----------
    energy : float
        Excited level energy.

    spinValue : str
        Spin value as a string '1/2', '5/2', etc.

    parity : str {'+', '-', ''} or None
        Level parity.

    lifetime : float
        Excited level lifetime.

    lifetime_units : str
        Lifetime units.

    Attributes
    ----------
    energy : float
        Excited level energy

    spinValue : str
        Excited level spin, represented by a string. Example: '1/2', '5/2', etc.

    parity : str {'-', '+', ''}
        Excited level parity.

    level_linewidth: float
        Level linewidth on the plot, default value is 0.5

    color : str {'black', 'red', 'green', etc.} or RGB code
        Level line color. Default value is 'black'.

    linestyle : str {'solid', 'dashed'}
        Level linestyle.

    lifetime : float
        Level lifetime.

    Methods
    -------
    highlight(linewidth=4, color='red')
        Changes instance's linewidth and color attributes.

    """

    def __init__(self, energy, spinValue=None, parity=None, lifetime=None, lifetime_units=None):
        """The __init__ method creates Level object and sets up instance's attributes values
        with given parameter values.

        """


        self.energy = energy
        self.spinValue = spinValue
        self.parity = parity
        self.level_linewidth = 0.5
        self.color = 'black' #RGB codes
        self.linestyle = 'solid'
        self.lifetime = lifetime
        self.lifetime_units = lifetime_units

        #todo: get rid of highlit method or write one for transitions
        self.highlighted = False


    def highlight(self, linewidth=4, color='red'):
        self.color= color
        self.highlight_linewidth = linewidth
        self.highlighted = True


    def getLineStyle(self):
        if self.linestyle=='dashed':
            return (1, (5, 10))

    def __str__(self):
        return 'Level object (energy = {} \t spinValue = {} \t parity = {} \t lifetime = {})'.format(self.energy, self.spinValue, self.parity, self.lifetime)



class Transition():
    """This is class for transitions of the nuclear states with emission of a gamma ray. The class instance contains all
     information about transition itself and its plotting style.

    Parameters
    ----------
    gammaEnergy : float
        Excited level energy.

    from_lvl : float
        Energy of the state in which the nuclei was **before** gamma transition.

    to_lvl : float
        Energy of the state in which the nuclei was **after** gamma transition.

    gammaEnergy_err : float
        Excited level energy error value (default value is None).

    intensity : float
        Intensity of the transition (default value is None).

    intensity_err : float
        Energy of the level in which the nuclei was before gamma transition (default value is None).

    multipolarity : str
        Multipolarity of the gamma ray

    Attributes
    ----------
    gammaEnergy : float

    from_lvl : float

    to_lvl : float

    gammaEnergy_err : float

    intensity : float

    instensity_err : float

    transition_linewidth: float
        Transition linewidth on the plot, default value is 0.001. Be careful, there is different scale of width in use, in comparison to class Level.

    color : str {'black', 'red', 'green', etc.} or RGB code
        Level line color. Default value is 'black'.

    linestyle : str {'solid', 'dashed'}
        Level linestyle.

    lifetime : float


    """

    def __init__(self, gammaEnergy, from_lvl, to_lvl, gammaEnergy_err=None, intensity=None, instensity_err=None, multipolarity=None):
        """The __init__ method creates Transition object and sets up instance's attributes values
        with given parameter values.

        """
        self.gammaEnergy = gammaEnergy
        self.from_lvl = from_lvl
        self.to_lvl = to_lvl
        self.gammaEnergy_err = gammaEnergy_err
        self.intensity = intensity
        self.intensity_err = instensity_err
        self.multipolarity = multipolarity

        self.transition_linewidth = 0.001
        self.color = 'black'
        self.linestyle='solid'

    def getLineStyle(self):
        if self.linestyle=='dashed':
            return (1, (5, 10))


    def transitionDescription(self):
        """
        Returns transition description as a string.

        :return: str 'E (dE)  I (dI)'

        """
        transitionDescription = ''
        if self.gammaEnergy:
            transitionDescription += '{}'.format(self.gammaEnergy)
            if self.gammaEnergy_err:
                transitionDescription += '({})'.format(self.gammaEnergy_err)
        if self.intensity:
            transitionDescription += '   {}'.format(self.intensity)
            if self.intensity_err:
                transitionDescription += '({})'.format(self.intensity_err)
        if self.multipolarity:
                transitionDescription += self.multipolarity

        return transitionDescription


    def __str__(self):
        string = 'Transition object (gamma energy = {} \t from level = {} \t to level = {})'.format(self.gammaEnergy, self.from_lvl, self.to_lvl)

        return string



class PackageDict(OrderedDict):
    """
    Creates collections.OrderedDict object with an additional function of splitting dictionaries, and changing
    simultaneously attributes values of all objects placed in the dictionary.

    :return: list of two PackageDict_objects
    """

    def slice(self, from_key, to_key):
        """

        :param from_key: str key from which we start slicing  PackageDict_object
        :param to_key:  str gamma transition energy to which we slice PackageDict_object
        :return: sliced PackageDict_object
        """

        newDict = PackageDict()

        for key in self.keys():
            if float(key) >= float(from_key) and float(key) <= float(to_key):
                newDict[key] = self[key]
        return newDict




class Database_csv():
    """
    Create database from csv file.

    Parameters
    ----------
    lvlFileName : str
        File which contains lvls description.

    transitionsFileName : str
        File which contains transitions description.

    Attributes
    ----------
    levels : pandas.DataFrame
        Contains levels information.

    transitions : pandas.DataFrame
        Contains transitions information.

    """

    def __init__(self, lvlFileName, transitionsFileName):
        self.levels = pd.read_csv(lvlFileName, header=0, sep='\s+')
        self.transitions = pd.read_csv(transitionsFileName, header=0, sep='\s+', keep_default_na=False)

    def slice(self, gamma_start_lvl, gamma_end_lvl):
        # has to be tested!
        Database_xlsx_slice = self.transitions.loc[
            (self.transitions['from_lvl'] <= gamma_end_lvl) | (self.transitions['to_lvl'] >= gamma_start_lvl)]
        return Database_xlsx_slice

    def levelsPackage(self):
        """
        Creates dictionary of Level_objects

        :return: ordered dictionary of Level_objects with keys equal to energy {'energy' : Level_object }
        """

        levels_dictionary = PackageDict()
        for index, row in self.levels.iterrows():
            levels_dictionary[str(row.lvl_energy)] = Level(energy=row.lvl_energy, spinValue=row.spin, parity=row.parity)
        return levels_dictionary

    def transitionsPackage(self):
        """
        Creates dictionary of Transition_objects

        :return: ordered dictionary of Transition objects with keys equal to the transition's energy {'energy' : Transition_object }
        """
        
        
        transitions_dictionary = PackageDict()
        for index, row in self.transitions.iterrows():
            transitions_dictionary[str(row.g_energy)] = Transition(gammaEnergy=row.g_energy, from_lvl=row.from_lvl, to_lvl=row.to_lvl,\
                                                        intensity=row.I, instensity_err=row.dI, gammaEnergy_err=row.g_energy_err)
        return transitions_dictionary









class Database_xlsx(Database_csv):
    """
    Create database from xlsx file. This classs inherited methods from Database_csv class.

    Parameters
    ----------
    databaseFileName : str
        File which contains lvls description.


    Attributes
    ----------
    levels : pandas.DataFrame
        Contains levels information.

    transitions : pandas.DataFrame
        Contains transitions information.

    """
    def __init__(self, databaseFileName):
        self.levels = pd.read_excel(databaseFileName, sheet_name='levels', keep_default_na=False, skip_blank_lines=True)
        self.transitions = pd.read_excel(databaseFileName, sheet_name='transitions', keep_default_na=False, skip_blank_lines=True)




if __name__ == '__main__':
    Database_xlsx=Database_xlsx(databaseFileName='./data/DATABASE.xlsx')
    print(Database_xlsx.levels)
    package = Database_xlsx.transitionsPackage()
    newPackage = package.split(from_key='155.5', to_key='1001.4')
    print(newPackage.keys())

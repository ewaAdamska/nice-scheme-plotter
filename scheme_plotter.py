from database_reader import Database
from collections import OrderedDict
import matplotlib.pyplot as plt

class Level():
    def __init__(self, energy, spinValue=None, parity=None, lifetime=None):
        self.energy = energy
        self.spinValue = spinValue
        self.parity = parity
        self.level_linewidth = 0.5
        self.color = 'black' #RGB codes
        self.linestyle = 'solid'
        self.lifetime = lifetime

        self.highlighted = False


    def highlight(self, linewidth=4, color='red'):
        self.color= color
        self.highlight_linewidth = linewidth
        self.highlighted = True


    def _linestyle(self):
        if self.linestyle=='dashed':
            return (1, (5, 10))

    def __str__(self):
        return 'Level object (energy = {} \t spinValue = {} \t parity = {} \t lifetime = {})'.format(self.energy, self.spinValue, self.parity, self.lifetime)



class Transition():

    def __init__(self, gammaEnergy, from_lvl, to_lvl, gammaEnergy_err=None, intensity=None, instensity_err=None):
        self.gammaEnergy = gammaEnergy
        self.from_lvl = from_lvl
        self.to_lvl = to_lvl
        self.gammaEnergy_err = gammaEnergy_err
        self.intensity = intensity
        self.intensity_err = instensity_err

        self.transition_linewidth = 0.001
        self.color = 'black'
        self.linestyle='solid'

    def _linestyle(self):
        if self.linestyle=='dashed':
            return (1, (5, 10))


    def transitionDescription(self):

        transitionDescription = ''
        if self.gammaEnergy:
            transitionDescription += '{}'.format(self.gammaEnergy)
            if self.gammaEnergy_err:
                transitionDescription += '({})'.format(self.gammaEnergy_err)
        if self.intensity:
            transitionDescription += '   {}'.format(self.intensity)
            if self.intensity_err:
                transitionDescription += '({})'.format(self.intensity_err)

        return transitionDescription


    def __str__(self):
        string = 'Transition object (gamma energy = {} \t from level = {} \t to level = {})'.format(self.gammaEnergy, self.from_lvl, self.to_lvl)

        return string

############################################################################################################################################################
############################################################################################################################################################



def levelsPackage(database):
    # TODO: maybe its better to omitt this step with dict (???) lets see what will be more useful
    # creating a dictionary {"energy value string" : Level object}
    levels_dictionary = OrderedDict()
    for index, row in database.levels.iterrows():
        levels_dictionary[str(row.lvl_energy)] = Level(energy=row.lvl_energy, spinValue=row.spin, parity=row.parity)
    return levels_dictionary


def transitionsPackage(database):
    # TODO: maybe its better to omitt this step with dict (???) lets see what will be more useful
    # creating a dictionary {"energy value string" : Transition object}
    transitions_dictionary = OrderedDict()
    for index, row in database.transitions.iterrows():
        transitions_dictionary[str(row.g_energy)] = Transition(gammaEnergy=row.g_energy, from_lvl=row.from_lvl, to_lvl=row.to_lvl,\
                                                    intensity=row.I, instensity_err=row.dI, gammaEnergy_err=row.g_energy_err)
    return transitions_dictionary


############################################################################################################################################################
############################################################################################################################################################


class Scheme():
    # These attributes must be Class-Attributes, because when we create many instances of Scheme class,
    # we want them to be identically set up. For example: if we split our decay scheme for many pages
    # we create separated instances of Scheme class for each page. If we decide to change font size
    # or any other scheme's geometry property we want to change it for all Scheme objects.


    # publics:
    figureWidth = 20
    scalingHeightFactor = 0.6 # 0.7 for A4
    dpi = 75

    # bug! zmiana tych wartosci wszystko psuje
    schemeWidth = 10000
    schemeHeight = 7000


    fontSize = 14
    transition_fontSize = 12

    spinAnnotationWidthFactor = 0.04
    energyAnnotationWidthFactor = 0.04

    spinAnnotationSlopeFactor = 0.01
    energyAnnotationSlopeFactor = 0.01


    transtitionsSpacingFactor = 0.021


    # private Class instances:
    _number_of_schemes = 0


    def __init__(self, **kwargs):

        if kwargs is not None:
            for key, value in kwargs.items():
                if key in Scheme.__dict__.keys(): #this is checking if we are not creating new, not necessary atributes
                    setattr(self, key, value)


        # These attributes must be Instance-attributes because they are specified for each Scheme instance
        # object, separately. They are also private attributes, its not good to change them from outside
        # of class code.
        # privs:
        self._spinAnnotationStartingPoint = 0

        self._lastAnnotationPointHeight = 0
        self._annotationBoxHeight = 200  # TODO: this might be scalled automatically with font size

        self.__setPlotGeometry()
        self.__prepareCanvas()

        #updating Class Atribute:
        #counting number of Scheme instances
        Scheme._number_of_schemes += 1

    #TODO: add 'set' functions for all important atributes

    def __setPlotGeometry(self):

        self._energyAnnotationSlope = self.energyAnnotationSlopeFactor * self.schemeWidth
        self._spinAnnotationSlope = self.spinAnnotationSlopeFactor * self.schemeWidth


        self._spinAnnotationStartingPoint = 0
        self._spinAnnotationEndingPoint = self.spinAnnotationWidthFactor * self.schemeWidth
        self._spinAnnotationWidth_value = self._spinAnnotationEndingPoint - self._spinAnnotationStartingPoint
        self._spinAnnotationTextPoint = self._spinAnnotationWidth_value / 2


        self._energyAnnotationStartingPoint = (1 - self.energyAnnotationWidthFactor)* self.schemeWidth
        self._energyAnnotationEndingPoint = self.schemeWidth
        self._energyAnnotationWidth_value = self._energyAnnotationEndingPoint - self._energyAnnotationStartingPoint
        self._energyAnnotationTextPoint = self.schemeWidth - self._energyAnnotationWidth_value / 2


        self._levelLineStartingPoint = self._spinAnnotationEndingPoint + self._spinAnnotationSlope
        self._levelLineEndingPoint = self._energyAnnotationStartingPoint-self._energyAnnotationSlope
        self._levelLineWidth_value = self._levelLineEndingPoint - self._levelLineStartingPoint


        self._firstArrowPoint = self._levelLineEndingPoint-0.02*self.schemeWidth #first Arrow Point
        self._nextArrowPoint =  self._firstArrowPoint #will be updated
        self._transitionsSpacingValue = self._levelLineWidth_value * self.transtitionsSpacingFactor


    def enableLatex(self):
        plt.rcParams.update({"text.usetex" : True})

    def __prepareCanvas(self):
        fig, ax = plt.subplots(figsize=(self.figureWidth, self.scalingHeightFactor * self.figureWidth), dpi=self.dpi)
        plt.subplots_adjust(left=0.01, right=0.99)

        plt.rcParams.update({'font.size': self.fontSize}) # setting up font for all labels


        plt.axis('off')
        plt.ylim(-10, self.schemeHeight)
        plt.xlim(0, self.schemeWidth)


    def addLevel(self, Level_object):

        #### TODO: this part can be improved
        self.annotationLvl = Level_object.energy

        while self.annotationLvl < self._lastAnnotationPointHeight:
            self.annotationLvl += self._annotationBoxHeight

        self._lastAnnotationPointHeight = self.annotationLvl + self._annotationBoxHeight



        ######## TODO ^^^

        def addLevelLine(energy):
            if Level_object.highlighted == False:
                plt.plot([self._levelLineStartingPoint, self._levelLineEndingPoint], [energy, energy], 'k-', lw=Level_object.level_linewidth, color=Level_object.color, linestyle=Level_object._linestyle())
            else:
                plt.plot([self._levelLineStartingPoint, self._levelLineEndingPoint], [energy, energy], 'k-',
                         lw=Level_object.highlight_linewidth, color=Level_object.color)

        def addSpin(spinValue, parityValue, energy):
            # h is additional height of splitted part of level line
            #TODO: annotation width should be scalled by using self.energyAnnotationStartingPoint etc. (!!!)

            if parityValue=='-' or parityValue=='+':
                spinAnnotationString = r'${}^{}$'.format(spinValue, parityValue)
            else:
                spinAnnotationString = ''

            plt.plot([self._spinAnnotationStartingPoint,self._spinAnnotationEndingPoint], [self.annotationLvl, self.annotationLvl], 'k-', lw=Level_object.level_linewidth)
            plt.plot([self._spinAnnotationStartingPoint,self._spinAnnotationEndingPoint], [self.annotationLvl, self.annotationLvl], 'k-', lw=Level_object.level_linewidth)
            plt.plot([self._spinAnnotationEndingPoint,self._levelLineStartingPoint], [self.annotationLvl, energy], 'k-', lw=Level_object.level_linewidth)
            plt.text(x=self._spinAnnotationTextPoint, y=(self.annotationLvl)+0.01*self.schemeHeight, s=spinAnnotationString, size=self.fontSize, horizontalalignment='center')


        def addEnergy(energyValue, energy):
            # h is additional height of splitted part of level line
            plt.plot([self._energyAnnotationStartingPoint, self._energyAnnotationEndingPoint], [self.annotationLvl, self.annotationLvl], 'k-', lw=Level_object.level_linewidth)
            plt.plot([self._levelLineEndingPoint,self._energyAnnotationStartingPoint], [energy, self.annotationLvl], 'k-', lw=Level_object.level_linewidth)
            plt.text(x=self._energyAnnotationTextPoint, y=self.annotationLvl+0.01*self.schemeHeight, s=energyValue, size=self.fontSize, horizontalalignment='center')

        addLevelLine(energy=Level_object.energy)
        addSpin(spinValue=Level_object.spinValue, parityValue=Level_object.parity, energy=Level_object.energy)
        addEnergy(energyValue=str(Level_object.energy), energy=Level_object.energy)


    def addTransition(self, Transition_object):
        arrowHeadWidth = 0.005*self._levelLineWidth_value
        arrowHeadLength =  0.01*self._levelLineWidth_value

        plt.arrow(x=self._nextArrowPoint , y=Transition_object.from_lvl, dx=0, dy=-1*Transition_object.gammaEnergy,\
                  head_width=arrowHeadWidth, head_length=arrowHeadLength,
                    length_includes_head=True, facecolor=Transition_object.color, color=Transition_object.color,\
                    width=Transition_object.transition_linewidth, alpha=1, linestyle=Transition_object._linestyle())


        box = dict(boxstyle='square', facecolor='white', color='white', alpha=1, pad=0) #udalo sie zmienic rozmiar white box za pomoca parametru pad
        plt.text(x=self._nextArrowPoint, y=Transition_object.from_lvl+self.schemeHeight*0.002, s=Transition_object.transitionDescription(),\
                 fontsize = self.transition_fontSize, rotation=60, horizontalalignment='left', verticalalignment='bottom',\
                 bbox=box)


        self._nextArrowPoint -= self._transitionsSpacingValue


    def addLevelsPackage(self, levelsPackage):
        for key in levelsPackage.keys():
            self.addLevel(levelsPackage[key])

    def addTransitionsPackage(self, transitionsPackage):
        # -1 means reversed sorting
        for key in [t[0] for t in sorted(transitionsPackage.items(), key=lambda x: (x[1].from_lvl, -1 * x[1].to_lvl))]:
            self.addTransition(transitionsPackage[key])

    def addNucleiName(self, nucleiName=r'$^{63}$Ni'):
        plt.text(0.48, 0.05, nucleiName, fontsize=48, transform=plt.gcf().transFigure)

    def save(self, fileName=None):
        if fileName:
            pass
        else:
            fileName = 'scheme_part_{}.svg'.format(self._number_of_schemes)

        print('Scheme saved to the file {}'.format(fileName))
        plt.savefig(fileName)

    def show(self):
        plt.show()



if __name__ == '__main__':

    scheme = Scheme()


    levels = levelsPackage(database=Database(lvlFileName='DATABASE_LVLS', transitionsFileName='DATABASE_TRANS'))
    transitions = transitionsPackage(database=Database(lvlFileName='DATABASE_LVLS', transitionsFileName='DATABASE_TRANS'))



    levels['2696.3'].highlight(linewidth=2, color='red')
    levels['1324.01'].linestyle='dashed'


    transitions['5514.64'].linestyle = 'dashed'

    transitions['4142.5'].color = 'red'
    transitions['4142.5'].transition_linewidth = 5
    transitions['1371.3'].color = 'purple'
    transitions['2178.18'].color ='blue'
    transitions['2540.9'].color ='green'
    transitions['2696.8'].color = 'red'


    print(levels['4055.0'])
    print(transitions['86.8'])


    #scheme.enableLatex()

    scheme.addLevelsPackage(levelsPackage = levels)
    scheme.addTransitionsPackage(transitionsPackage = transitions)


    scheme.addNucleiName(r'$^{63}$Ni')


    scheme.show()


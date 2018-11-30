import matplotlib.pyplot as plt


class Scheme():
    """
    Creates scheme object with various methods for plotting gamma transitions scheme of the excited nuclei.


    Note
    ----
    These attributes must be Class-Attributes, because when we create many instances of Scheme class,
    we want them to be identically set up. For example: if we split our decay scheme for many pages
    we create separated instances of Scheme class for each page. If we decide to change font size
    or any other scheme's geometry property we want to change it for all Scheme objects.

    Attributes
    ----------
    figureWidth : float
        Class attribute. Output scheme window/canvas width. Default value is 20.

    figureHeight : float
        Class attribute. Output scheme window/canvas length. Default value is 12.

    dpi : int
        Class attribute. Output scheme window/canvas dpi factor. Default value is 75.

    fontSize : int
        Class attribute. Level labels font size. Default value is 14.

    transition_fontSize : int
        Class attribute. Transitions labels font size. Default value is 12.

    spinAnnotationWidthFactor : float
        Class attribute. Part of scheme plot width which will be taken by left sided annotation (spin and parity part). Default value is 0.04.

    energyAnnotationWidthFactor : float
        Class attribute. Part of scheme plot width which will be taken by right sided annotation (level energy). Default value is 0.04.

    spinAnnotationSlopeFactor : float
        Class attribute. Part of scheme plot width which will be taken for slope **on the left side**, when annotation and level line splitting
        is needed (this is needed when bunch of levels is closer to each other than annotation height. Default value is 0.01.

    energyAnnotationSlopeFactor : float
        Class attribute. Part of scheme plot width which will be taken for slope **on the right side**, when annotation and level line splitting
        is needed (this is needed when bunch of levels is closer to each other than annotation height. Default value is 0.01.

    transtitionsSpacingFactor : float
        Class attribute. Part of scheme plot width which will be taken as gap between transition arrows. Default value is 0.021.

    """

    # publics:
    figureWidth = 20
    figureHeight = 12 # 12 for A4
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


    # private Class attributes:
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
        self._annotationBoxHeight = 200

        self.__setPlotGeometry()
        self.__prepareCanvas()

        #updating Class Attribute:
        #counting number of Scheme instances
        Scheme._number_of_schemes += 1

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
        """
        Enables LaTeX rendering for all strings in the scheme plot.
        (!) This function has to be called **before**
        Scheme_object.addLevel(), Scheme_object.addLevelsPackage() methods (and analogously for add-transitions).
        """
        plt.rcParams.update({"text.usetex" : True})
        plt.rcParams["text.latex.preamble"].append(r'\usepackage[dvips]{graphicx}\usepackage{xfrac}')


    def __prepareCanvas(self):
        fig, ax = plt.subplots(figsize=(self.figureWidth, self.figureHeight), dpi=self.dpi)
        plt.subplots_adjust(left=0.01, right=0.99)

        plt.rcParams.update({'font.size': self.fontSize}) # setting up font for all labels


        plt.axis('off')
        plt.ylim(-10, self.schemeHeight)
        plt.xlim(0, self.schemeWidth)


    def addLevel(self, Level_object):
        """
        Plots level on the scheme.

        :param: Level_object
        """

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
        """
        Plots transition on the scheme.

        :param: Transition_object
        """
        arrowHeadWidth = 0.005*self._levelLineWidth_value
        arrowHeadLength =  0.01*self._levelLineWidth_value

        plt.arrow(x=self._nextArrowPoint , y=Transition_object.from_lvl, dx=0, dy=-1*Transition_object.gammaEnergy,\
                  head_width=arrowHeadWidth, head_length=arrowHeadLength,
                    length_includes_head=True, facecolor=Transition_object.color, edgecolor=Transition_object.color,\
                    width=Transition_object.transition_linewidth, alpha=1, linestyle=Transition_object._linestyle())


        box = dict(boxstyle='square', facecolor='white', edgecolor='white', alpha=1, pad=0) #udalo sie zmienic rozmiar white box za pomoca parametru pad
        plt.text(x=self._nextArrowPoint, y=Transition_object.from_lvl+self.schemeHeight*0.002, s=Transition_object.transitionDescription(),\
                 fontsize = self.transition_fontSize, rotation=60, horizontalalignment='left', verticalalignment='bottom',\
                 bbox=box)


        self._nextArrowPoint -= self._transitionsSpacingValue


    def addLevelsPackage(self, levelsPackage):
        """
        Plots all levels from the levels package (see more about levelsPackage).

        :param: levelsPackage
        """
        for key in levelsPackage.keys():
            self.addLevel(levelsPackage[key])

    def addTransitionsPackage(self, transitionsPackage):
        """
        Plots all transition from the transitions package (see more about transitionsPackage).

        :param: transitionsPackage
        """

        # -1 means reversed sorting
        for key in [t[0] for t in sorted(transitionsPackage.items(), key=lambda x: (x[1].from_lvl, -1 * x[1].to_lvl))]:
            self.addTransition(transitionsPackage[key])

    def addNucleiName(self, nucleiName=r'$^{63}$Ni'):
        """
        Adds nuclei name to the decay scheme.

        :param: nucleiName : *str* (best option is to use LaTeX typing method. Example: nucleiName=r'$^{63}$Ni')
        """
        plt.text(0.48, 0.05, nucleiName, fontsize=48, transform=plt.gcf().transFigure)

    def save(self, fileName=None):
        """
        Saves plot to the file.
        :param: fileName: filename. It is recommended to use .svg extension, for example fileName='my_scheme.svg'. It is
        also allowed to **not pass** any file name (especially if there will be more than one Scheme_object plots saved
        during code operation. The Scheme class will enumerate all of it's instances, and later save them to different
        files. Example: ::

        >>> s1 = Scheme()
        >>> s2 = Scheme()
        >>> s3 = Scheme()
        >>> ...
        >>> s1.save()
        >>> s2.save()
        >>> s3.save()
        In the result three files will be created: ``scheme_part_1.svg``, ``scheme_part_2.svg`` and ``scheme_part_3.svg``.
        It is useful when scheme splitting for many pages is needed.

        """
        if fileName:
            pass
        else:
            fileName = 'scheme_part_{}.svg'.format(self._number_of_schemes)

        print('Scheme saved to the file {}'.format(fileName))
        plt.savefig(fileName)

    def show(self):
        """
        Shows resulting scheme.
        """
        plt.show()



if __name__ == '__main__':
    from database_reader import *

    scheme = Scheme()

    ##reading database from xlsx file (it's also possible to read csv)
    dataBase = Database_xlsx('./data/DATABASE.xlsx')

    ## reading dictionaries of Level objects, and Transitions objects
    levels = dataBase.levelsPackage()
    transitions = dataBase.transitionsPackage()


    ## setting up levels lines color, style, width, etc.
    levels['2696.3'].highlight(linewidth=2, color='red')
    levels['1324.01'].linestyle = 'dashed'

    ## setting up transitions lines color, style, width, etc.
    transitions['5514.64'].linestyle = 'dashed'

    transitions['4142.5'].color = 'red'
    transitions['4142.5'].transition_linewidth = 5


    transitions['2540.9'].color = 'green'

    transitions['2696.8'].color = 'red'


    ##It is possible to print Level or Transition object (it will show its the most important properties)
    # print(levels['4055.0'])
    # print(transitions['86.8'])

    ## It is possible to render scheme with labels written in LaTeX
    scheme.enableLatex()

    ## Plotting all levels and transitions in packages
    scheme.addLevelsPackage(levelsPackage = levels)
    scheme.addTransitionsPackage(transitionsPackage = transitions)


    ## Plotting nuclei name
    scheme.addNucleiName(r'$^{63}$Ni')


    ## Showing plot
    scheme.show()

    ## Saving to the file
    scheme.save('example.svg')
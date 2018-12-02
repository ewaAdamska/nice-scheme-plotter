# from nice_scheme_plotter import database_reader, nice_scheme_plotter
from nice_scheme_plotter import *


# In this section it is possible to change default values of the Scheme class attributes
nice_scheme_plotter.Scheme.transtitionsSpacingFactor = 0.024



## Reading database from xlsx file (it's also possible to read csv)
dataBase = database_reader.Database_xlsx('data/DATABASE.xlsx')

## Reading dictionaries of Level objects, and Transitions objects
levels = dataBase.levelsPackage()
transitions = dataBase.transitionsPackage()

## Setting up levels lines color, style, width, etc.
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

## Preparing new Scheme object
scheme = nice_scheme_plotter.Scheme()

## It is possible to render scheme with labels written in LaTeX. It is not recommended to use LaTeX rendering
# for previewing the scheme, because it takes longer time.
# scheme.enableLatex()

## Plotting all levels and transitions in previously created packages.
scheme.addLevelsPackage(levelsPackage=levels)
scheme.addTransitionsPackage(transitionsPackage=transitions)

## Plotting nuclei name.
scheme.addNucleiName(r'$^{63}$Ni')

## Showing plot
scheme.show()

## Saving to the file.
scheme.save('example.svg')
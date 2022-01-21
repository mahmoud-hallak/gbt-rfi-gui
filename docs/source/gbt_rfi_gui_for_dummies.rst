.. _GBTRFIGUIForDummies:

GBT RFI GUI For Dummies
=============

Summary
-----

The GUI is in place to facilitate the retrieval and analysis of GBT RFI data. This is done through an easy-to-use GUI (graphical user interface) called gbt_rfi_gui. This GUI is written in python and makes use of pyQt, an interface creator. Through pyQt the program is able to display a window containing options for the user to specify in order to obtain relevant data to their project. This project also makes use of django to access the database data itself. As well as pandas to organize the data and matplotlib for plotting.

The primary audience of the project is an observer, with an observation, that they would like to get RFI information on. Under this working definition, the user can specify: receiver/s, frequency range of interest, and target date (whether or not this date is in the past or the future) and date range (either 30 days or 365 days).

The project will take these specifications and will only retrieve and display data: in that frequency range, from that receiver/s, and the target date specified range ( more on target date below). This data will then be plotted in 2 ways:

    In a 2D line plot of the time-averaged intensity vs. frequency

    In a color plot of the intensity, plotted per session, as a function of frequency (this only occurs if there is >1 session per the time range specified)

Explained above is the general layout for the GUI, there are several other features that will now be briefly mentioned.

    Save Button: if the save option is checked the user can opt to save the raw data, from the entered specifications, to a csv file to the location of their choosing

    Menu Buttons: there are menu options such as 'quit' and 'about'

    Zoom Features: there are built in zoom and range features offered by matplotlib in the plotting interfaces

Target Date
~~~~

The target date is used to get them the most relevant data available. The program will extrapolate in the specified range (30 or 365 days) to the target date and attempt to retrieve data, if there is no data this is not a worthwhile search for the observer. To make it worthwhile, the program will then search, backwards in time, for the most recent session with data. This data will then be returned, along with a specified-range extrapolation from that new most-recent-session date.



Code Walk-through - for 'dummies'
------

Set up the GUI
~~~~

First section is the init class. This will set up anything needed for the GUI.

Here the buttons are connected from the UI (user interface) to the program. There are several buttons to connect including: receivers panel, start and end frequency options, target date calendar, plot button, menu buttons (about and quit).

Now, once these buttons are clicked, triggered, or manipulated by the user, they will fire off code blocks in gbt_rfi_gui.py.


Plot Button Clicked
~~~~

When the plot button is clicked it begins a chain of 'reactions' that will allow the user to access the data in a meaningful way.

First the receivers selections is gathered from the UI. Then the target date and frequency. These user selections are then given to the do_plot function.

This function gathers data, from the database tables Frequency and Scan. It filters out any data that is not included in the specified receivers or in the date or frequency range, in that order. It then creates a plot-able configuration out of that data by making it into a pandas Data Frame. This data then goes down two paths.

1. The mean is taken of the intensity as a function of time - then it is plotted, via matplotlib, as a 2D plot of the Mean Intensity vs. Frequency

2. (if >1 session per range) it is used in the function ``make_color_plot`` where 'bins' are created for frequency and time. These bins are of size 1MHz and 1Day respectively. Then the intensity is plotted per session as a function of frequency in the form of a imshow/ColorPlot

In this function, after the plotting, if the save button is checked then there is the option for the user to save the raw data to a location of their choosing. QFileDialog is used here to create a popup for the user to select a location as well as a name for the resultant csv file.


About Menu Button Clicked
~~~~

This menu button will trigger a QMessage Box, or pop-up, to display relevant information or links about the program


Quit Menu Button Clicked
~~~~

This menu button will cause the program to cleanly close, and displays a good-bye message.

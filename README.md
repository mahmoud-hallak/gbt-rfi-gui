# GBT_RFI_Query
Result of the GREAT (GBO RFI Environment Analysis Tools) project. Used as a tool by users to convey the current or past impact of the RFI on their projects.

## Installation
This repo is currently configured to work only with the GBO network, relying on databases and environments availble on our internal machines. This can be adapted to outside use if those references are re-configured.

# How to configure GBT_RFI_Query
Included in this repo are several items: ingestion scripts to add data to our reference DB, the gbt_rfi_gui and the RFI Webpage. To configure all of these, see below.

1. To get the gbt_rfi_query
```
    # Then do the below
    git clone https://github.com/GreenBankObservatory/gbt-rfi-gui.git
    cd gbt_rfi_query
    # make and source a new venv
    ~gbosdd/pythonversions/3.9/bin/python -m venv <path/vevnName>
    source <path/vevnName>/bin/activate
    pip install -U pip setuptools wheel build
    pip install -r requirements.txt
    pip install -e .
```
2. Set up your environment to access the relevant databases
```
	cp rfi_query/.env.template rfi_query/.env
	# Modify the contents of this file to point to a "legacy" RFI DB and a "new" RFI DB - reach out to gbosdd if a password or access is needed
```
3. Run the website from your development location
```
	# source your venv
	./manage.py runserver 0.0.0.0:9437
	# then navigate to the webpage on your browser at: <machine>:9437
```
4. Run the GUI
```
	# source your venv
	python gbt_rfi_gui.py
```


# Docs
## What is GREAT?
This project currently includes the gbt-rfi-gui, , the RFI pipeline, , RFI databases, and now the RFI website! How do all of these processes work together and how do we collect, analyse and report data? Read below to find out!

1. Data is collected from the telescope and added to the gbtdata area in the form of fits files.
2. Data is converted into .txt files and stored in the GBTDataImages area by the RFI_pipeline
	- RFI_pipeline is called by a crontab which is running a version of the gbtrfipipeline.sh executable
3. Data is then added to the legacy database and table `rfi_data:MasterRFICatalog`, again through a RFI_pipeline upload function
	- This is a mySQL database
4. Since this table was inherited and has a rather basic schema, we will then re-ingest it to a more verbose database, rfi_query
	- This is a postGRES database
5. Then we have two options to present our data: GUI or website
	1. GUI: This is a more compact display method, where the path to getting data for the user is very straightforward. We are able to get the user what they need but it lacks a lot of bells and whistles that the website can account for. One big downside is that it can only be internally accessed
		- How the GUI works: there is a .ui file that will populate the GUI window on the first run of the python scripts.
		- Then when the user selects their data and clicks submit several python functions begin to query the data, filter the data to the user's specifications, plot the data as both a line and color plot and finally display the plots as matplotlib windows.
			- There is also the option to save the data as a csv if selected
	2. Website: Here we ahve more options for features and development, while also having the option to display our tool publicilly or to add outside observatories to our displayed data!
		- How the website works: First we must know what the user wants to look at. We can ask them what they are interested in through a django query page. This page lives as the landing page for the GREAT website. We are able to allow for several input options: receiever, start and end date, most relevant data date, and begin and end frequency. This is done through a django crispy_form.
		- Once the user imputs their selections django will process that query in the views.graph() function and return the results of the user's query.
		-  This data is then used by plotly to create a line and color plot of the data, and subsequently displayed on the webpage under the query specific url

To learn more about each of these features please see below.

## What is GREAT: GUI
The GUI is in place to facilitate the retrieval and analysis of GBT RFI data. This is done through an easy-to-use GUI (graphical user interface) called gbt-rfi-gui. This GUI is written in python and makes use of pyQt, an interface creator. Through pyQt the program is able to display a window containing options for the user to specify in order to obtain relevant data to their project. This project also makes use of django to access the database data itself. As well as pandas to organize the data and matplotlib for plotting.

The primary audience of the project is an observer, with an observation, that they would like to get RFI information on. Under this working definition, the user can specify: receiver/s, frequency range of interest, and date range (this date can be in the past or the future via start and end date - no longer than 365 day range).

The project will take these specifications and will only retrieve and display data: in that frequency range, from that receiver/s, and the target date specified range

### How to use the GUI
The GUI has been released as of March 2022. This means that it lives in the default environment at GBO as a package. This package can be run from any machines command line (in the network) as

```
$ gbt-rfi-gui
```

This gui will then pop-open and you can feed it information. You can use any parameters to test, I generally use Rcvr2_3 and a 2-4week time range.

Science side documentaion on the GUI: https://greenbankobservatory.org/rfi-gui-user-guide/


## What is GREAT: Website
The website is a offshoot of the GREAT (GBO RFI Environment Analysis Tools) project.

Our website serves to be an all access tool to interface RFI data to those interested. This is to be done in a easy-to-use, easy-to-access format which just so happened to be a django backend website. Here we are able to query the RFI databases for information pertaining to the user's specifications and display them in a clear and concise way.
Our plots will display the data (mjd, intensity, frequency, projID) based on the user's specifications (receiver, mjd, freq_low, freq_high)

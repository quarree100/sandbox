# MIT License

# Copyright (c) 2022 Joris Zimmermann

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the “Software”), to
# deal in the Software without restriction, including without limitation the
# rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
# sell copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS IN THE SOFTWARE.

"""Plot a Sankey chart from an Excel spreadheet.

Create a ``Sankey`` plot as png, svg and html with data from an Excel file.
Uses ``Sankey.xlsx`` in the same directory per default, but can be started
from the command line to load any other file. One Sankey is created for
each sheet in the Excel file.

For more info on creating Sankeys with HoloViews, see
http://holoviews.org/reference/elements/bokeh/Sankey.html

"""

import os
import logging
import pandas as pd
import holoviews as hv
from bokeh.io import export_png, export_svgs, show, output_file, webdriver
from bokeh.layouts import gridplot

# Define the logging function
logger = logging.getLogger(__name__)


def main():
    """Define user input, create plot and produce the output."""
    setup()  # Perform some setup stuff

    # Read in data as Pandas DataFrame (file name can be given via parser)
    file_load = run_OptionParser(file_default='Sankey.xlsx')
    df_dict = pd.read_excel(file_load, header=0, sheet_name=None)

    sankey_list = []

    # Try to create sankey for each sheet in the workbook
    for sheet_name, df in df_dict.items():
        logger.info(sheet_name)
        if logger.isEnabledFor(logging.INFO):
            print(df)  # Show imported DataFrame on screen

        # Use same name as input file, plus sheet_name
        filename = os.path.splitext(file_load)[0]+' '+str(sheet_name)

        try:
            # Create the plot figure from DataFrame
            bkplot = create_and_save_sankey(df, filename, sheet_name)
            sankey_list += [bkplot]  # Add result to list of sankeys

        except Exception as ex:
            logger.exception(ex)  # todo
            logger.error(str(sheet_name)+': '+str(ex))

    # Create html output
    output_file(os.path.splitext(file_load)[0] + '.html',
                title=os.path.splitext(file_load)[0])
    show(gridplot(sankey_list, ncols=1, sizing_mode='stretch_width'))


def create_and_save_sankey(edges, filename=None, title='', title_html='',
                           edge_color_index='To', show_plot=False,
                           fontsize=11, label_text_font_size='17pt',
                           node_width=45, export_title=False):
    """Use HoloViews to create a Sankey plot from the input data.

    Args:
        edges (DataFrame): Pandas DataFrame with columns 'From', 'To' and
        'Value'. Names are arbitrary, but must match ``edge_color_index``.

        filename (str): Filename (without extension) of exported png and svg.

        title (str): Diagram title for html output.

        edge_color_index (str, optional): Name of column to use for edge
        color. With 'To', all edges arriving at a node have the same color.
        Defaults to 'To'.

    Returns:
        bkplot (object): The Bokeh plot object.

    """
    try:
        # If export_png or export_svgs are called repeatedly, by default
        # a new webdriver is created each time. For me, on Windows, those
        # webdrivers survive the script and the processes keep running
        # in task manager.
        # A solution is to manually define a webdriver that we can actually
        # close automatically:
        web_driver = webdriver.create_firefox_webdriver()
    except Exception as e:
        logger.exception(e)
        web_driver = None

    hv.extension('bokeh')  # Some HoloViews magic to make it work with Bokeh

    # Define a custom color palette
    palette = ['#f14124', '#ff8021', '#e8d654', '#5eccf3', '#b4dcfa',
               '#4e67c8', '#56c7aa', '#24f198', '#2160ff', '#c354e8',
               '#e73384', '#c76b56', '#facdb4']
    # Alternative: Dictionary of colors related to entries in edges DataFrame.
    # All undefined entries will be grey.
    # palette = {'A': '#f14124', 'B': '#ff8021', 'C': '#e8d654',
    #            'D': '#5eccf3', 'E': '#b4dcfa', 'F': '#4e67c8',
    #            'G': '#56c7aa', 'H': '#24f198', 'I': '#2160ff',
    #            'J': '#c354e8', 'K': '#e73384', 'L': '#c76b56',
    #            'M': '#facdb4',
    #            'X': '#5eccf3', 'Y': '#b4dcfa', 'Z': '#4e67c8',
    #            }

    # Only keep non-zero rows (flow with zero width cannot be plotted)
    edges = edges.loc[(edges != 0).all(axis=1)]

    # Use HoloViews to create the plot
    hv_sankey = hv.Sankey(edges).options(
        width=1400, height=600,
        edge_color_index=edge_color_index,
        cmap=palette,
        edge_cmap=palette,
        node_width=node_width,  # default 15
        fontsize=fontsize,
        label_text_font_size=label_text_font_size,
        node_padding=10,  # default 10
        )

    # HoloViews is mainly used for creating html content. Getting the simple
    # PNG is a little more involved
    hvplot = hv.plotting.bokeh.BokehRenderer.get_plot(hv_sankey)
    bkplot = hvplot.state
    bkplot.toolbar_location = None  # disable Bokeh toolbar
    if export_title is True:  # Add the title to the file export
        bkplot.title.text = str(title)

    if filename is not None:
        # Create the output folder, if it does not already exist
        if not os.path.exists(os.path.abspath(os.path.dirname(filename))):
            os.makedirs(os.path.abspath(os.path.dirname(filename)))

        export_png(bkplot, filename=filename+'.png', webdriver=web_driver)
        bkplot.output_backend = 'svg'
        export_svgs(bkplot, filename=filename+'.svg', webdriver=web_driver)

    if web_driver is not None:
        web_driver.quit()  # Quit webdriver after finishing using it

    # For html output
    bkplot.title.text = str(title)
    bkplot.sizing_mode = 'stretch_width'

    if filename is not None:
        if title_html == '':
            title_html = title
        # Create html output
        output_file(filename + '.html', title=title_html)

    if show_plot:
        show(bkplot)

    return bkplot


def setup():
    """Set up the logger."""
    log_level = 'INFO'
    logger.setLevel(level=log_level.upper())  # Logger for this module
    logging.getLogger('holoviews').setLevel(level='ERROR')
    logging.basicConfig(format='%(asctime)-15s %(levelname)-8s %(message)s')


def run_OptionParser(file_default=None):
    """Define and run the argument parser. Return the chosen file path."""
    import argparse

    description = 'Plot a Sankey chart from an Excel spreadheet.'
    parser = argparse.ArgumentParser(description=description,
                                     formatter_class=argparse.
                                     ArgumentDefaultsHelpFormatter)

    parser.add_argument('-f', '--file', dest='file', help='Path to an Excel '
                        'spreadsheet.', type=str, default=file_default)

    args = parser.parse_args()

    return args.file


if __name__ == '__main__':
    """This code is executed when the script is started"""
    try:  # Wrap everything in a try-except to show exceptions with the logger
        main()
    except Exception as e:
        logger.exception(e)
        input('\nPress the enter key to exit.')  # Prevent console from closing

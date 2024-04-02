import xmlrpc from 'xmlrpc';
import createScatterplot from 'regl-scatterplot';

function getCurrentTimestamp() {
    const now = new Date();
    const timestamp = now.toISOString().replace(/T/, ' ').replace(/\..+/, '');
    return `[${timestamp}]`;
}


const originalConsoleLog = console.log;
// Override console.log to include timestamps
console.log = function() {
    const timestamp = getCurrentTimestamp();
    const args = [timestamp, ...arguments];
    originalConsoleLog.apply(console, args);
};


// RPC client for communicating with the python backend.
const client = xmlrpc.createClient({ host: 'localhost', port: 8000, path: '/RPC2' });

// Loads the h5mu file by sending a 'load_h5mu' method call
function loadH5MU(file) {
    // Call the load_h5mu method on the server with the file path
    client.methodCall('load_h5mu', [file.name], function(error, result) {
        if (error)
        {
            console.error('Error:', error);
        }
        else {
            console.log('H5MU file loaded successfully:', result);
            // Once loaded, test if data object is saved
            client.methodCall('return_num_cells', [], function(error, numCells) {
                if (error) {
                    console.error('Error:', error);
                } else {
                    console.log('Number of cells:', numCells);
                }
            });
        }
    });
}


// Gets the plotly html using 'return_umap_scatter_html' call and displays that html.
function displayUMAPPlotly() {
    // Record the start time before RPC call
    var startTime = performance.now();

    // Call the return_umap_scatter_html method on the server
    client.methodCall('return_umap_scatter_html', [], function(error, htmlContent) {
        if (error) {
            console.error('Error:', error);
        }
        else {
            // Calculate the time taken for the RPC call
            var endTime = performance.now();
            var timeTaken = endTime - startTime;
            console.log('Time taken for RPC call (ms):', timeTaken);

            // Get the size of the htmlContent string
            console.log('Length of htmlContent:', htmlContent.length);

            //console.log('Received HTML content: ', htmlContent);
            
            // Append the received HTML content to the umapContainerPlotly using jQuery
            $('#umapContainerPlotly').append(htmlContent);
            console.log('Done placing html content to div');
        }
    });
}


async function displayUMAPRegl() {
    const canvas = document.querySelector('#canvas');
    const { width, height } = canvas.getBoundingClientRect();
    const scatterplot = createScatterplot({
        canvas,
        width,
        height,
        pointSize: 4,
        opacity: 0.5,
        performanceMode: false
    });  

    console.log("Making RPC call");
    // Record the start time before RPC call
    var startTime = performance.now();
    const umapData = await new Promise((resolve, reject) => {
        client.methodCall('return_normalized_umap_coords', [], function(error, data) {
            if (error) {
                console.error('Error:', error);
                reject(error); // Reject the promise if there's an error
            } else {
                // Calculate the time taken for the RPC call
                const endTime = performance.now();
                const timeTaken = endTime - startTime;
                console.log('Time taken for RPC call (ms):', timeTaken);
                resolve(data); // Resolve the promise with the data
            }
        });
    });

    const pointoverHandler = (pointId) => {
        const x = umapData[0][pointId];
        const y = umapData[1][pointId];
        const category = umapData[2][pointId];
        const cell_type = umapData[3][category];
        const cell_id = umapData[4][pointId];

        // Update the content of the #pointHover div
        const pointInfoDiv = document.getElementById('pointHover');
        pointInfoDiv.innerHTML = `
          <p><strong>Cell Index:</strong> ${cell_id}</p>
          <p><strong>Cell Type:</strong> ${cell_type}</p>          
          <p><strong>X:</strong> ${x.toFixed(2)}</p>
          <p><strong>Y:</strong> ${y.toFixed(2)}</p>
        `;
      };

    const selectHandler = ({points: selectedPoints}) => {
        const pointsSelectDiv = document.getElementById('pointsSelect');
        pointsSelectDiv.innerHTML = `
          <p><strong>Points selected:</strong> ${selectedPoints.length}</p>
        `;
    }

    const deselectHandler = () => {
        const pointsSelectDiv = document.getElementById('pointsSelect');
        pointsSelectDiv.innerHTML = '';
    }

    console.log('Drawing scatter plot');
    scatterplot.clear();
    // plotly colors
    let cellTypeColors = [
        "#8dd3c7",
        "#ffffb3",
        "#bebada",
        "#fb8072",
        "#80b1d3",
        "#fdb462",
        "#b3de69",
        "#fccde5",
        "#d9d9d9",
        "#bc80bd"
    ]

    scatterplot.set({'colorBy': 'valueA', 'pointColor': cellTypeColors});
    scatterplot.subscribe('pointover', pointoverHandler);
    scatterplot.subscribe('select', selectHandler);
    scatterplot.subscribe('deselect', deselectHandler);

    scatterplot.draw({
        x: umapData[0],
        y: umapData[1],
        valueA: umapData[2]
        });
    // create legend
    let legendContainer;
    // Check if the legend container already exists
    if (!legendContainer) {
        // If it doesn't exist, create a new one
        legendContainer = document.createElement('div');
        legendContainer.id = 'legendContainer';
        document.getElementById('umapContainerRegl').appendChild(legendContainer);
    }

    // Clear previous content
    legendContainer.innerHTML = '';

    // Assuming umapData[3] contains the cell types associated with the colors
    const cellTypes = umapData[3];

    // Create legend elements dynamically based on cellTypes and cellTypeColors
    cellTypes.forEach((cellType, index) => {
        const legendItem = document.createElement('div');
        legendItem.classList.add('legend-item');

        const legendColor = document.createElement('div');
        legendColor.classList.add('legend-color');
        legendColor.style.backgroundColor = cellTypeColors[index];

        const legendText = document.createElement('div');
        legendText.classList.add('legend-text');
        legendText.textContent = cellType;

        legendItem.appendChild(legendColor);
        legendItem.appendChild(legendText);
        legendContainer.appendChild(legendItem);
    });
    console.log('Done drawing scatter plot');

}

// Attach change event listener to file input element.
document.getElementById('fileInput').addEventListener('change', function(event) {
    const file = event.target.files[0];
    loadH5MU(file);
});

// Attach click event listener to the Draw UMAP buttons.
document.getElementById('drawUmapButtonPlotly').addEventListener('click', function() {
    displayUMAPPlotly();
});
document.getElementById('drawUmapButtonRegl').addEventListener('click', function() {
    displayUMAPRegl();
});



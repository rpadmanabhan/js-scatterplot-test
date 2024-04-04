import { tableFromIPC } from 'apache-arrow';
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



function loadH5MU(file) {
    console.log('Starting to load H5MU file');
    
    // Prepare form data with file object
    const formData = new FormData();
    formData.append('file', file);

    // Send POST request to the server
    fetch('http://localhost:3002/load_h5mu', {
        method: 'POST',
        body: formData
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('HTTP request failed');
        }
        return response.json();
    })
    .then(result => {
        console.log('H5MU file loaded successfully:', result);

        // Once loaded, test if data object is saved correctly
        fetch('http://localhost:3002/return_num_cells')
        .then(response => response.json())
        .then(numCells => {
            console.log('Number of cells:', numCells);
        })
        .catch(error => {
            console.error('Error:', error);
        });
    })
    .catch(error => {
        console.error('Error:', error);
    });
}


async function displayUMAPPlotly() {
    var startTime = performance.now();
    // Make HTTP request to get the plotly html div
    const plotly_div = await (await fetch("http://localhost:3002/return_plotly_html_div")).json();
    var endTime = performance.now();
    var timeTaken = endTime - startTime;
    console.log('Time taken for HTTP request (ms):', timeTaken)

    // Get the size of the plotly_div string
    console.log('Length of plotly_div:', plotly_div.length);
    //console.log('Received HTML content: ', plotly_div);
    
    // Append the received HTML content to the umapContainerPlotly using jQuery
    $('#umapContainerPlotly').append(plotly_div);
    console.log('Done placing html content to div');
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

    console.log("Making HTTP request");

    // Get the x,y, cell_types (as ints) and cell indices for the umap plot
    const table = await tableFromIPC(fetch("http://localhost:3002/return_normalized_umap_coords_pyarrow"));
    // To test 5M points:
    //const table = await tableFromIPC(fetch("http://localhost:3002/return_simulated_normalized_umap_coords_pyarrow"));
    console.log("Read HTTP return into apache arrow table")

    // Get the cell types corresponding to the integer point labels
    const cell_type_labels = await (await fetch("http://localhost:3002/unique_cell_types")).json();
    
    // create a umapData array with relevant info
    const umapData = [
        table.getChild('umap_coords_X').data[0].values,
        table.getChild('umap_coords_Y').data[0].values,
        table.getChild('cell_types').data[0].values,
        table.getChild('cell_indices').data[0].values
    ];

    // function to handle hover action
    const pointoverHandler = (pointId) => {
        const x = umapData[0][pointId];
        const y = umapData[1][pointId];
        const category = umapData[2][pointId];
        const cell_type = cell_type_labels[category];
        const cell_id = umapData[3][pointId];        

        // Update the content of the #pointHover div
        const pointInfoDiv = document.getElementById('pointHover');
        pointInfoDiv.innerHTML = `
          <p><strong>Cell Index:</strong> ${cell_id}</p>
          <p><strong>Cell Type:</strong> ${cell_type}</p>          
          <p><strong>X:</strong> ${x.toFixed(2)}</p>
          <p><strong>Y:</strong> ${y.toFixed(2)}</p>
        `;
      };

    // function to handle selection action
    const selectHandler = ({points: selectedPoints}) => {
        const pointsSelectDiv = document.getElementById('pointsSelect');
        pointsSelectDiv.innerHTML = `
          <p><strong>Points selected:</strong> ${selectedPoints.length}</p>
        `;
    }

    // function for deselect action
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

    // Create legend elements dynamically based on cell_type_labels
    for (let index = 0; index < cell_type_labels.length; index++) {
        const cellType = cell_type_labels[index];
    
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
    }
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



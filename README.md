# js-scatterplot-test

Test code for evaluating the [regl-scatterplot](https://github.com/flekschas/regl-scatterplot). It consists of a Flask backend server exposing trivial loading of a muon file and returning the stored UMAP coordinates. The javascript front end then plots this data as a scatterplot.

## Start the python backend
```
# Ensure you are in a virtual environment
pip install -r requirements.txt
flask --app server_flask.py run --port 3002
```

## Build the javascript front-end and serve using express

```
# install deps
npm install
# build
npm run build
# start
node server.js
```

## To test the 5M simulated dataset
Uncomment the below line in `index.js` (and comment out the other line):

```//const table = await tableFromIPC(fetch("http://localhost:3002/return_simulated_normalized_umap_coords_pyarrow"));```


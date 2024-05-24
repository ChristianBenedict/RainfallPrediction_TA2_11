document.addEventListener('DOMContentLoaded', function () {
  var socket = io.connect('http://' + document.domain + ':' + location.port);

  var data = [{
    x: [],
    y: [],
    type: 'line',
    marker: {
      color: 'blue'
    }
  }];

  var layout = {
    xaxis: { title: 'Tanggal' },
    yaxis: { title: 'Curah Hujan', automargin: true, margin: { b: -30 } }
  };

  Plotly.newPlot('chart', data, layout);

  socket.on('update', function () {
    updatePlotly();
  });

  function updatePlotly() {
    fetch('/get_prediction_data')
      .then(response => response.json())
      .then(newData => {
        let timestamps = [];
        let rainfalls = [];
        newData.forEach(entry => {
          timestamps.push(new Date(entry.timestamp).toLocaleDateString());
          rainfalls.push(entry.curah_hujan);
        });
  
        let trace = {
          x: timestamps,
          y: rainfalls,
          type: 'line'
        };
  
        let layout = {
          title: 'Grafik Curah Hujan Harian',
          xaxis: { title: 'Tanggal' },
          yaxis: { title: 'Curah Hujan' }
        };
  
        Plotly.newPlot('chart', [trace], layout);
      })
      .catch(error => console.error('Error fetching data:', error));
  }
  
});

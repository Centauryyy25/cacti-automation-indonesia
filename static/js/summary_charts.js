(function(){
  var ctx = document.getElementById('pieChart');
  if(!ctx || !window.SUMMARY_DATA){ return; }
  var data = window.SUMMARY_DATA;
  var chart = new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: ['Success','Fail'],
      datasets: [{
        data: [data.success || 0, data.fail || 0],
        backgroundColor: ['#2ecc71','#e74c3c'],
        borderWidth: 0
      }]
    },
    options: {
      plugins: { legend: { labels: { color: '#eaeaea' } } },
      responsive: true,
      maintainAspectRatio: false
    }
  });
})();

function fetchBlocks() {
    axios.get('/blocks')
        .then(response => {
            const blocksDiv = document.getElementById('blocks');
            blocksDiv.innerHTML = '';
            response.data.forEach(block => {
                blocksDiv.innerHTML += `
                    <div style="border: 1px solid #ccc; margin: 10px; padding: 10px;">
                        <p>Block #${block.index}</p>
                        <p>Hash: ${block.hash}</p>
                        <p>Data: ${block.data}</p>
                    </div>
                `;
            });
        });
}

// Initial load
fetchBlocks();

// Refresh every 2 seconds
setInterval(fetchBlocks, 2000);

document.addEventListener('DOMContentLoaded', function() {
    const checkFoodSafetyButton = document.getElementById('checkFoodSafety');
    checkFoodSafetyButton.addEventListener('click', uploadAndIdentify);

    function uploadAndIdentify() {
        const imageUpload = document.getElementById('imageUpload');
        const file = imageUpload.files[0];

        if (!file) {
            alert('Please select an image.');
            return;
        }

        // 1. Upload to Firebase Storage
        const storageRef = firebase.storage().ref('user_images/' + file.name); // Choose a storage path
        const uploadTask = storageRef.put(file);

        uploadTask.on('state_changed',
            (snapshot) => {
                // You can add upload progress updates here if needed
            },
            (error) => {
                console.error('Upload failed:', error);
                alert('Image upload failed.');
            },
            () => {
                // 2. Get the Download URL
                storageRef.getDownloadURL().then((downloadURL) => {
                    console.log('File available at:', downloadURL);

                    // 3. Send the URL to Flask for Vision API processing
                    fetch('/', {  // Assuming your Flask route is '/'
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({ image_url: downloadURL }),
                    })
                    .then(response => response.json())
                    .then(data => {
                        // 4. Update the UI with the result
                        const resultDiv = document.querySelector('.result');
                        if (data.food) {
                            resultDiv.innerHTML = `<p>Food: <span class="math-inline">\{data\.food\}</p\><p\></span>{data.message}</p>`;
                        } else {
                            resultDiv.innerHTML = `<p>No food recognized.</p>`;
                        }
                    })
                    .catch((error) => {
                        console.error('Error:', error);
                        alert('Error processing image.');
                    });
                });
            }
        );
    }
});
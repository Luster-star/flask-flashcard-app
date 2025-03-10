from flask import Flask, render_template, request, jsonify
import os
import pandas as pd
import random

app = Flask(__name__)

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# 파일 크기 제한 (10MB까지 가능)
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  

@app.route('/')
def index():
    return '''
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>플래시카드</title>
        <style>
            body { font-family: Arial, sans-serif; text-align: center; margin-top: 50px; }
            #flashcard { 
                width: 60%; 
                height: 200px; /* 기존보다 2배 커짐 */
                margin: 20px auto; 
                padding: 30px; 
                border: 2px solid #333; 
                font-size: 36px; /* 기존보다 1.5배 커짐 */
                font-weight: bold;
                display: flex;
                align-items: center;
                justify-content: center;
            }
            .button-group {
                margin-top: 20px;
            }
            .control-group {
                margin-top: 30px;
            }
            button { margin: 10px; padding: 10px 20px; font-size: 16px; border: none; background: none; cursor: pointer; }
            .control-btn { font-size: 24px; }
        </style>
    </head>
    <body>

        <h1>영어 단어 플래시카드</h1>
        <input type="file" id="fileInput">
        <button onclick="uploadFile()">📂 파일 업로드</button>
        <div id="flashcard">여기에 단어가 표시됩니다.</div>
        
        <div class="button-group">
            <button onclick="startFlashcards('words_only')">단어만</button>
            <button onclick="startFlashcards('words_with_meaning')">단어+해석</button>
        </div>
        
        <div class="control-group">
            <button class="control-btn" id="toggleBtn" onclick="toggleFlashcards()">⏸️</button>
        </div>

        <script>
            let wordsOnly = [];
            let wordsWithMeaning = [];
            let index = 0;
            let mode = "words_only";
            let isPaused = false;
            let timeoutId;

            function uploadFile() {
                const fileInput = document.getElementById('fileInput');
                const file = fileInput.files[0];
                if (!file) {
                    alert('파일을 선택해주세요.');
                    return;
                }
                const formData = new FormData();
                formData.append('file', file);

                fetch('/upload', {
                    method: 'POST',
                    body: formData
                })
                .then(response => response.json())
                .then(data => {
                    if (data.error) {
                        alert(data.error);
                    } else {
                        wordsOnly = data.words_only;
                        wordsWithMeaning = data.words_with_meaning;
                        alert('업로드 성공!');
                        document.getElementById('flashcard').innerText = "준비 완료!";
                    }
                })
                .catch(error => {
                    console.error('Error:', error);
                    alert('파일 업로드 중 오류가 발생했습니다.');
                });
            }

            function startFlashcards(selectedMode) {
                if (wordsOnly.length === 0) {
                    alert('먼저 파일을 업로드해주세요.');
                    return;
                }
                mode = selectedMode;
                isPaused = false;
                document.getElementById("toggleBtn").innerText = "⏸️";
                showNext();
            }

            function toggleFlashcards() {
                isPaused = !isPaused;
                document.getElementById("toggleBtn").innerText = isPaused ? "▶️" : "⏸️";
                if (!isPaused) {
                    showNext();
                } else {
                    clearTimeout(timeoutId);
                }
            }

            function playPronunciation(word) {
                let utterance = new SpeechSynthesisUtterance(word);
                utterance.lang = 'en-US';
                let voices = speechSynthesis.getVoices();
                utterance.voice = voices.find(voice => voice.lang === 'en-US' && voice.name.includes('Female')) || 
                                  voices.find(voice => voice.lang === 'en-US' && voice.name.includes('Samantha')) || 
                                  voices.find(voice => voice.lang === 'en-US' && voice.name.includes('Google US English')) ||
                                  voices.find(voice => voice.lang === 'en-US');
                speechSynthesis.speak(utterance);
            }

            speechSynthesis.onvoiceschanged = () => {
                let voices = speechSynthesis.getVoices();
                console.log("Available voices:", voices);
            };

            function showNext() {
                if (isPaused || index >= wordsOnly.length) {
                    return;
                }
                if (mode === "words_only") {
                    document.getElementById('flashcard').innerText = wordsOnly[index];
                    timeoutId = setTimeout(() => {
                        index++;
                        showNext();
                    }, 3000);
                } else {
                    let currentPair = wordsWithMeaning[index];
                    document.getElementById('flashcard').innerText = currentPair[0]; // 단어 표시
                    playPronunciation(currentPair[0]); // 발음 재생
                    timeoutId = setTimeout(() => {
                        if (!isPaused) {
                            document.getElementById('flashcard').innerText = currentPair[1]; // 해석 표시
                            timeoutId = setTimeout(() => {
                                index++;
                                showNext();
                            }, 3000);
                        }
                    }, 3000);
                }
            }
        </script>

    </body>
    </html>
    '''

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': '파일을 선택해주세요.'})
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': '선택된 파일이 없습니다.'})
    
    filepath = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(filepath)
    
    try:
        if file.filename.endswith('.csv'):
            df = pd.read_csv(filepath, usecols=[0, 2], header=None)
        else:
            df = pd.read_excel(filepath, usecols=[0, 2], header=None, engine='openpyxl')
        
        word_pairs = [(str(row[0]), str(row[2]) if pd.notna(row[2]) else "") for _, row in df.iterrows()]
        random.shuffle(word_pairs)
        words_only, words_with_meaning = zip(*word_pairs) if word_pairs else ([], [])
    except Exception as e:
        return jsonify({'error': f'파일을 처리하는 중 오류 발생: {str(e)}'})
    
    words_only = list(words_only) + ["FINISH!"]
    words_with_meaning = list(words_with_meaning) + [("FINISH!", "")]
    
    return jsonify({'words_only': words_only, 'words_with_meaning': list(zip(words_only, words_with_meaning))})

if __name__ == '__main__':
    app.run(debug=True)

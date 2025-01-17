import streamlit as st
import requests
import time
import io
import tempfile
import os
from pydub import AudioSegment
from constants import ASSEMBLYAI_API_KEY

ASSEMBLYAI_API_KEY = st.secrets['ASSEMBLYAI_API_KEY']
headers = {'authorization': ASSEMBLYAI_API_KEY}

class AudioProcessor:
    def __init__(self):
        self.headers = headers
        self.audio_path = None
        self.audio_segment = None
    
    def save_audio_file(self, uploaded_file):
        """Save uploaded file to temporary file and load as AudioSegment"""
        try:
            # Create temporary file
            suffix = os.path.splitext(uploaded_file.name)[1]
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_file:
                # Write uploaded file content to temporary file
                tmp_file.write(uploaded_file.getvalue())
                self.audio_path = tmp_file.name
            
            # Load audio file as AudioSegment
            self.audio_segment = AudioSegment.from_file(self.audio_path)
            return True
        except Exception as e:
            st.error(f"Error saving audio file: {str(e)}")
            return False
    
    def upload_to_assemblyai(self, file):
        """Upload audio file to AssemblyAI"""
        upload_url = 'https://api.assemblyai.com/v2/upload'
        try:
            response = requests.post(upload_url, headers=self.headers, files={'file': file})
            response.raise_for_status()
            return response.json()['upload_url']
        except Exception as e:
            st.error(f"File upload failed: {str(e)}")
            return None

    def request_transcription(self, audio_url):
        """Request transcription with speaker labels"""
        transcript_endpoint = 'https://api.assemblyai.com/v2/transcript'
        json_data = {
            'audio_url': audio_url,
            'speaker_labels': True,
            'language_code': 'en_us'
        }
        
        try:
            response = requests.post(transcript_endpoint, headers=self.headers, json=json_data)
            response.raise_for_status()
            return response.json()['id']
        except Exception as e:
            st.error(f"Transcription request failed: {str(e)}")
            return None

    def poll_transcription(self, transcript_id):
        """Poll for transcription completion"""
        status_endpoint = f"https://api.assemblyai.com/v2/transcript/{transcript_id}"
        
        while True:
            try:
                response = requests.get(status_endpoint, headers=self.headers)
                response.raise_for_status()
                result = response.json()
                
                if result['status'] == 'completed':
                    return result
                elif result['status'] == 'error':
                    st.error(f"Transcription failed: {result.get('error', 'Unknown error')}")
                    return None
                
                time.sleep(5)
            except Exception as e:
                st.error(f"Error polling transcription: {str(e)}")
                return None

    def extract_audio_segment(self, start_ms, end_ms):
        """Extract audio segment from the loaded AudioSegment"""
        try:
            if self.audio_segment is None:
                raise Exception("No audio file loaded")
            
            # Extract segment
            segment = self.audio_segment[start_ms:end_ms]
            
            # Export segment to bytes
            buffer = io.BytesIO()
            segment.export(buffer, format="mp3")
            return buffer.getvalue()
            
        except Exception as e:
            st.error(f"Error extracting audio segment: {str(e)}")
            return None

    def cleanup(self):
        """Clean up temporary files"""
        if self.audio_path and os.path.exists(self.audio_path):
            try:
                os.unlink(self.audio_path)
            except Exception as e:
                st.warning(f"Error cleaning up temporary file: {str(e)}")

def main():
    st.set_page_config(page_title="Speaker Separation & Transcription", layout="wide")
    
    st.title("Speaker Separation & Audio Transcription")
    st.subheader("Upload an audio file for speaker diarization and transcription")
    
    # Initialize processor
    processor = AudioProcessor()
    
    # File uploader
    uploaded_file = st.file_uploader("Choose an audio file", type=["mp3", "wav", "m4a"])
    
    if uploaded_file:
        if processor.save_audio_file(uploaded_file):
            st.info("File uploaded successfully. Click 'Process Audio' to start.")
            
            if st.button("Process Audio"):
                try:
                    # Process the audio file
                    with st.spinner("Uploading audio file..."):
                        audio_url = processor.upload_to_assemblyai(uploaded_file)
                    
                    if audio_url:
                        with st.spinner("Starting transcription..."):
                            transcript_id = processor.request_transcription(audio_url)
                        
                        if transcript_id:
                            with st.spinner("Processing... (this may take a few minutes)"):
                                result = processor.poll_transcription(transcript_id)
                            
                            if result:
                                st.success("Processing completed!")
                                
                                # Create tabs for different views
                                tab1, tab2 = st.tabs(["Transcript", "Statistics"])
                                
                                with tab1:
                                    st.subheader("Speaker Separated Transcription")
                                    for utterance in result.get('utterances', []):
                                        start_time = int(utterance['start']) // 1000
                                        minutes = start_time // 60
                                        seconds = start_time % 60
                                        formatted_time = f"{minutes:02}:{seconds:02}"
                                        
                                        # Create columns for timestamp, speaker label, text, and audio player
                                        col1, col2, col3, col4 = st.columns([1, 1, 4, 2])
                                        
                                        with col1:
                                            st.write(f"[{formatted_time}]")
                                        with col2:
                                            st.write(f"Speaker {utterance['speaker']}:")
                                        with col3:
                                            st.write(utterance['text'])
                                        with col4:
                                            # Extract and display audio segment
                                            audio_segment = processor.extract_audio_segment(
                                                utterance['start'],
                                                utterance['end']
                                            )
                                            if audio_segment:
                                                st.audio(audio_segment, format='audio/mp3')
                                
                                with tab2:
                                    st.subheader("Speaker Statistics")
                                    speakers = {}
                                    for utterance in result.get('utterances', []):
                                        speaker = utterance['speaker']
                                        if speaker not in speakers:
                                            speakers[speaker] = {
                                                'word_count': 0,
                                                'duration': 0
                                            }
                                        speakers[speaker]['word_count'] += len(utterance['text'].split())
                                        speakers[speaker]['duration'] += (utterance['end'] - utterance['start']) / 1000
                                    
                                    for speaker, stats in speakers.items():
                                        st.write(f"Speaker {speaker}:")
                                        st.write(f"- Words spoken: {stats['word_count']}")
                                        st.write(f"- Speaking time: {stats['duration']:.2f} seconds")
                finally:
                    # Clean up temporary files
                    processor.cleanup()

if __name__ == "__main__":
    main()
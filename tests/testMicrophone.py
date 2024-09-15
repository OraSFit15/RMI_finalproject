import unittest
from unittest.mock import patch, MagicMock
from RMI_Simulator.MRI_Test import MicrophoneRecorder

class TestMicrophoneRecorder(unittest.TestCase):

    @patch('pyaudio.PyAudio')
    def test_microphone_recorder(self, MockPyAudio):
        mock_audio = MagicMock()
        MockPyAudio.return_value = mock_audio

        recorder = MicrophoneRecorder()
        self.assertTrue(recorder.is_microphone_ready())
        recorder.start()
        recorder.stop()
        mock_audio.open.assert_called()
        recorder.close()
        mock_audio.terminate.assert_called_once()

if __name__ == '__main__':
    unittest.main()

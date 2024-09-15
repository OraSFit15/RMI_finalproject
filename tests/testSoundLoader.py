import unittest
from unittest.mock import patch, MagicMock
from RMI_Simulator.MRI_Test import SoundLoader

class TestSoundLoader(unittest.TestCase):

    @patch('pygame.mixer.Sound')
    def test_sound_loader(self, MockSound):
        mock_sound = MagicMock()
        MockSound.return_value = mock_sound

        sound_loader = SoundLoader('fake_path')
        sound_loader.run()

        MockSound.assert_called_once_with('fake_path')
        self.assertEqual(sound_loader.sound, mock_sound)

if __name__ == '__main__':
    unittest.main()

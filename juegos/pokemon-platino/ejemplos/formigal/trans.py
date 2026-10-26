import sys
from faster_whisper import WhisperModel
m = WhisperModel('large-v3', device='cpu', compute_type='int8')
for f in sys.argv[1:]:
    seg, info = m.transcribe(f, language='es', initial_prompt='Formigal, nuggets, birra, macarrones con tomate, espaguetis o lasañas, nevera.')
    print('==', f)
    for s in seg: print('%.1f-%.1f %s' % (s.start, s.end, s.text))

import unittest
from pathlib import Path
from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).resolve().parents[1] / 'app.py')


def button(app, label):
    return next(b for b in app.button if b.label == label)


def page(app):
    """Todo o texto da tela: markdown e blocos HTML (st.html)."""
    parts = [m.value for m in app.markdown]
    parts += [str(h.proto.body) for h in app.get('html')]
    return '\n'.join(parts)


class InterfaceTests(unittest.TestCase):
    def test_clicks_persistence_tariff_reset_and_legacy(self):
        app = AppTest.from_file(APP).run()
        self.assertEqual(len(app.exception), 0)
        self.assertIn('Computador desta simulação', page(app))
        self.assertIn('EnergySim', page(app))
        self.assertIn('Dentro do esperado para a tarefa', page(app))
        self.assertNotIn('Classe', page(app))
        self.assertTrue(button(app, '2. Simular otimização').disabled)
        initial = app.session_state['quick_demo'].snapshot()['power']['total_w']

        button(app, '1. Mostrar consumo extra').click().run()
        self.assertEqual(len(app.exception), 0)
        self.assertIn('Alerta: consumo acima do esperado', page(app))
        self.assertIn('80,2 W acima', page(app))
        self.assertNotEqual(initial, app.session_state['quick_demo'].snapshot()['power']['total_w'])

        button(app, '2. Simular otimização').click().run()
        self.assertEqual(len(app.exception), 0)
        self.assertEqual(initial, app.session_state['quick_demo'].snapshot()['power']['total_w'])
        self.assertIn('Dentro do esperado para a tarefa', page(app))
        self.assertIn('19,44', page(app))
        app.run()
        self.assertIn('19,44', page(app))
        app.number_input(key='demo_tariff').set_value(1.8).run()
        self.assertIn('38,88', page(app))

        # Grande escala: 30 PCs x R$ 38,88/mês x 12 meses com tarifa de R$ 1,80
        self.assertIn('E em grande escala?', page(app))
        self.assertIn('13.997', page(app))
        app.number_input(key='scale_pcs').set_value(10).run()
        self.assertEqual(len(app.exception), 0)
        self.assertIn('4.666', page(app))
        self.assertIn('O que fazer no dia a dia', page(app))

        button(app, 'Recomeçar').click().run()
        self.assertEqual(app.session_state['quick_demo'].stage, 'normal')
        self.assertIsNone(app.session_state['quick_demo'].comparison())
        button(app, 'Explorar o modo completo').click().run()
        self.assertEqual(app.session_state['screen'], 'intro_problema')
        self.assertEqual(len(app.exception), 0)
        button(app, 'Voltar à demonstração rápida').click().run()
        self.assertEqual(app.session_state['screen'], 'demo')
        self.assertEqual(len(app.exception), 0)

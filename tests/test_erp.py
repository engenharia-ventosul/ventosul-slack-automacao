import glob
import os
import shutil
import tempfile
import unittest
import xml.etree.ElementTree as ET
from unittest.mock import MagicMock, patch
import requests
import config
from servicos import erp
class TestErp(unittest.TestCase):
    def setUp(self):
        self._pasta_temp = tempfile.mkdtemp(prefix="ventosul-erp-test-")
        self._pasta_original = config.ERP_XML_DROP_FOLDER
        config.ERP_XML_DROP_FOLDER = self._pasta_temp
    def tearDown(self):
        config.ERP_XML_DROP_FOLDER = self._pasta_original
        shutil.rmtree(self._pasta_temp, ignore_errors=True)
    @patch("servicos.erp.requests.post")
    def test_webhook_ok_ainda_grava_xml_fallback(self, mock_post):
        mock_post.return_value = MagicMock(status_code=200, raise_for_status=lambda: None)
        payload = erp.despachar_para_erp("obra.criado", {"nome_obra": "Shopping X"}, canal_id="C1", nome_canal="obra-shopping-x")
        mock_post.assert_called_once()
        self.assertTrue(payload["_webhook_enviado"])
        self.assertTrue(os.path.exists(payload["_xml_fallback"]))
    @patch("servicos.erp.requests.post", side_effect=requests.exceptions.ConnectionError("ERP fora do ar"))
    def test_webhook_falha_nao_impede_xml(self, mock_post):
        payload = erp.despachar_para_erp("obra.criado", {"nome_obra": "Shopping X"}, canal_id="C1", nome_canal="obra-shopping-x")
        self.assertFalse(payload["_webhook_enviado"])
        self.assertTrue(os.path.exists(payload["_xml_fallback"]))
    def test_xml_contem_todos_os_campos(self):
        valores = {"nome_obra": "Shopping X", "escopo_tecnico": ["vrf", "dutos"]}
        caminho = erp.gravar_xml_para_vba(erp._payload_base("obra.criado", "C1", "obra-x", valores))
        arvore = ET.parse(caminho)
        raiz = arvore.getroot()
        self.assertEqual(raiz.attrib["evento"], "obra.criado")
        campos = {c.attrib["nome"]: c.text for c in raiz.find("Dados")}
        self.assertEqual(campos["nome_obra"], "Shopping X")
        self.assertEqual(campos["escopo_tecnico"], "vrf, dutos")
    def test_cria_a_pasta_se_nao_existir(self):
        config.ERP_XML_DROP_FOLDER = os.path.join(self._pasta_temp, "subpasta", "inbox")
        caminho = erp.gravar_xml_para_vba(erp._payload_base("teste", None, None, {}))
        self.assertTrue(os.path.exists(caminho))
    @patch("servicos.erp.requests.post")
    def test_um_xml_por_chamada(self, mock_post):
        mock_post.return_value = MagicMock(status_code=200, raise_for_status=lambda: None)
        erp.despachar_para_erp("a", {}, canal_id="C1", nome_canal="x")
        erp.despachar_para_erp("b", {}, canal_id="C1", nome_canal="x")
        arquivos = glob.glob(os.path.join(self._pasta_temp, "*.xml"))
        self.assertEqual(len(arquivos), 2)
if __name__ == "__main__":
    unittest.main()

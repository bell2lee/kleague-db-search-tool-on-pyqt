import pymysql, sys, json, csv
from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt
import xml.etree.ElementTree as ET
NOTUSE = '사용안함'


class ExportManager:
    def __init__(self, data):
        self.data = data

    def exportJSON(self, fileName='klegue.json'):
        for row in self.data:
            row['BIRTH_DATE'] = str(row['BIRTH_DATE'])
        with open(fileName, "w") as outfile:
            json.dump(self.data, outfile, indent=4, ensure_ascii=False)

    def exportCSV(self, fileName='klegue.csv'):
        with open(fileName, 'w') as f:
            w = csv.writer(f)
            w.writerow(self.data[0].keys())
            for item in self.data:
                w.writerow(item.values())

    def exportXML(self, fileName='klegue.xml'):

        rootElement = ET.Element('Table')
        rootElement.attrib['name'] = 'player'

        for row in self.data:
            rowElement = ET.Element('Row')
            rootElement.append(rowElement)

            for columnName in list(row.keys()):
                if row[columnName] == None:  # NICKNAME, JOIN_YYYY, NATION 처리
                    rowElement.attrib[columnName] = ''
                else:
                    rowElement.attrib[columnName] = row[columnName]

                if type(row[columnName]) != str: # 형 변환 처리
                    rowElement.attrib[columnName] = str(row[columnName])

        ET.ElementTree(rootElement).write(fileName, encoding='utf-8', xml_declaration=True)


class DBManager:
    recentData = []
    fieldEnum = {
        'teamName': 'TEAM_ID',
        'position': 'POSITION',
        'originCountry': 'NATION',
        'height': 'HEIGHT',
        'weight': 'WEIGHT',
    }
    nullMatchValue = {
        'NATION': '대한민국',
        'POSITION': '미정',
    }
    def __init__(self, host, user, password, db):
        self.conn = pymysql.connect(host=host, user=user, password=password, db=db, charset='utf8')

    def query(self, sql, params):
        try:
            with self.conn.cursor(pymysql.cursors.DictCursor) as cursor:     # dictionary based cursor
                cursor.execute(sql, tuple(params))
                tuples = cursor.fetchall()
                return tuples
        except Exception as e:
            print(e)
            print(type(e))


    def select(self, options=[]):
        clearOptions = []
        for option in options:
            fieldName = self.fieldEnum[option['name']]

            if option['value'] != NOTUSE:
                if fieldName in self.nullMatchValue.keys() and self.nullMatchValue[fieldName] == option['value']:
                    option['value'] = None
                clearOptions.append(option)


        sql = "SELECT * FROM player %s" % (" WHERE " if clearOptions else " ")
        andWhether = False
        params = []
        for option in clearOptions:
            if option['value'] != NOTUSE:
                if andWhether:
                    sql += ' and '

                if not option['value']:
                    sql += self.fieldEnum[option['name']] + " IS NULL"
                else:
                    sql += self.fieldEnum[option['name']] + ((" >= " if option['type'] else " <= ")
                                                         if option['name'] in ['height', 'weight'] else
                                                         " = ") + " %s"
                if option['value']:
                    params.append(option['value'])
                andWhether = True
        tuples = self.query(sql, params)
        self.recentData = tuples
        return tuples

    def groupExec(self, functionName, field):
        sql='SELECT %s(%s) from player' % (functionName, field)
        params = ()
        tuples = self.query(sql, params)
        return tuples[0]['%s(%s)' % (functionName, field)]

    def groupByExec(self, field, projectField):
        sql = 'SELECT %s from player GROUP BY %s' % (projectField, field)
        params = ()
        tuples = self.query(sql, params)
        return tuples


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.dbManager = DBManager(host='localhost', user='', password='', db='')
        self.setupUI()

    def inputTextChanged(self):
        pass

    def exportOnClick(self):
        exportManager = ExportManager(self.dbManager.recentData)
        for radio, instance in self.exportRadios.items():
            if instance.isChecked():
                if instance.text() == '.JSON':
                    exportManager.exportJSON()
                elif instance.text() == '.CSV':
                    exportManager.exportCSV()
                else:
                    exportManager.exportXML()
        msg = QMessageBox()
        msg.setWindowTitle('Export')
        msg.setText('데이터를 저장했습니다. 현재 프로그램 디렉터리를 학인하세요.')
        msg.setStandardButtons(QMessageBox.Ok)
        msg.exec_()

    def resetOnClick(self):
        for name, field in self.inputFields.items():
            if str(type(field['inputBox'])) == "<class 'PyQt5.QtWidgets.QLineEdit'>":
                field['inputBox'].clear()
            else:
                field['inputBox'].setCurrentText(NOTUSE)

    def searchOnClick(self):
        options = []
        for name, field in self.inputFields.items():
            attrValue = ''
            if not field['inputBox'].currentText():
                field['inputBox'].setText(NOTUSE)
            attrValue = field['inputBox'].currentText()
            item = {'name': name, 'value': attrValue}
            if item['name'] in ['height', 'weight']:
                item['type'] = field['options'][1].isChecked()
            options.append(item)
        self.refreshTable(self.tableWidget, data=self.dbManager.select(options), header=self.tableHeader)


    def setupUI(self):
        self.setWindowTitle("Kleague DB Search Tool")
        self.setGeometry(0, 0, 1100, 600)
        self.inputFields = {
            'teamName': {
                'label': '팀명 :',
                'inputBox': QComboBox(),
            },
            'position': {
                'label': '포지션 :',
                'inputBox': QComboBox(),
            },
            'originCountry': {
                'label': '출신국 :',
                'inputBox': QComboBox(),
            },
            'height': {
                'label': '키 :',
                'inputBox': QComboBox(),
                'options': [QGroupBox('옵션'), QRadioButton('이상'), QRadioButton('이하')],
            },
            'weight': {
                'label': '몸무게 :',
                'inputBox': QComboBox(),
                'options': [QGroupBox('옵션'), QRadioButton('이상'), QRadioButton('이하')],
            },
        }

        self.buttons = {
            'reset': {
                'instance': QPushButton('초기화'),
                'exec': self.resetOnClick,
            },
            'search': {
                'instance': QPushButton('검색'),
                'exec': self.searchOnClick,
            },
        }

        searchLayout = QHBoxLayout()

        for name, field in self.inputFields.items():
            label = QLabel()
            label.setText(field['label'])
            field['label'] = label
            if 'label' in field:
                searchLayout.addWidget(field['label'])
            searchLayout.addWidget(field['inputBox'])

            if str(type(field['inputBox'])) != "<class 'PyQt5.QtWidgets.QComboBox'>":
                field['inputBox'].textChanged.connect(self.inputTextChanged)
            else:
                self.inputFields[name]['inputBox'].addItem(NOTUSE)
                fieldName = self.dbManager.fieldEnum[name]
                if fieldName in self.dbManager.nullMatchValue:
                    self.inputFields[name]['inputBox'].addItem(self.dbManager.nullMatchValue[fieldName])

                if name.lower() in ['height', 'weight']:
                    for i in range(self.dbManager.groupExec('min', name),
                                   self.dbManager.groupExec('max', name) + 1):
                        self.inputFields[name.lower()]['inputBox'].addItem(str(i))
                else:
                    fieldName = self.dbManager.fieldEnum[name]
                    for item in self.dbManager.groupByExec(fieldName, fieldName):
                        if item[fieldName]:
                            self.inputFields[name]['inputBox'].addItem(item[fieldName])

            if 'options' in field:
                groupLayout = QHBoxLayout()
                field['options'][1].setChecked(True)
                groupLayout.addWidget(field['options'][1])
                groupLayout.addWidget(field['options'][2])

                field['options'][0].setLayout(groupLayout)

                searchLayout.addWidget(field['options'][0])




        data = self.dbManager.select()
        self.tableHeader = list(data[0].keys())
        self.tableWidget = QTableWidget()
        self.refreshTable(table=self.tableWidget, data=data, header=self.tableHeader)
        mainLayout = QVBoxLayout()
        buttonLayout = QHBoxLayout()

        for button in self.buttons.values():
            button['instance'].clicked.connect(button['exec'])
            buttonLayout.addWidget(button['instance'])
        title = QLabel('Kleague DB search tool - 20171679 이종휘')
        title.font().setPointSize(300)
        font = title.font()
        font.setPointSize(26)
        font.setBold(True)
        title.setFont(font)

        title.setAlignment(Qt.AlignCenter)
        mainLayout.addWidget(title)
        mainLayout.addLayout(searchLayout)
        mainLayout.addLayout(buttonLayout)
        mainLayout.addWidget(self.tableWidget)

        self.exportRadios = {
            'json': QRadioButton('.JSON'),
            'csv': QRadioButton('.CSV'),
            'xml': QRadioButton('.XML'),
        }
        exportGroup = QGroupBox('파일로 내보내기')
        exportBtn = QPushButton('파일로 내보내기')
        exportBtn.clicked.connect(self.exportOnClick)
        exportLayout = QHBoxLayout()
        self.exportRadios['json'].setChecked(True)
        for radioName, radioInstance in self.exportRadios.items():
            exportLayout.addWidget(radioInstance)

        exportGroup.setLayout(exportLayout)
        mainLayout.addWidget(exportGroup)
        mainLayout.addWidget(exportBtn)
        self.setLayout(mainLayout)

    def refreshTable(self, table, data, header):
        table.clearContents()
        try:
            table.setRowCount(len(data))
        except TypeError:
            table.setRowCount(0)
        table.setColumnCount(len(header))

        table.setHorizontalHeaderLabels(header)
        for i, row in enumerate(data):
            for j, (k, v) in enumerate(row.items()):
                itemValue = self.dbManager.nullMatchValue[k] if not v and k in self.dbManager.nullMatchValue else str(v)
                table.setItem(i, j, QTableWidgetItem(itemValue))


        table.resizeColumnsToContents()
        table.resizeRowsToContents()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    mainWindow = MainWindow()
    mainWindow.show()
    app.exec_()
    mainWindow.dbManager.conn.close()
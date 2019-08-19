import subprocess
import os
import json


'''
All paths here, excepting `buildDir` and logName,
are relative to script directory.
`buildDir` is relative to source code directory.
`logName` is relative to executable directory.
'''
testAddr = 'git@github.com:kystyn/cmake_tester.git'
testDir = 'test'

studentAddr = 'git@github.com:kystyn/cmake_student.git'
studentDir = 'student'

buildDir = 'build'

generatorCMakeParam = 'Ninja'
generator = 'ninja'

packageName = 'lesson'

logName = 'log.txt'
jsonFile = 'test_result.json'

'''
Update (or init, if wasn't) repository function.
ARGUMENTS:
    - git repository address:
        repoAddress
    - local directory name to pull
      (relatively to script path):
        repoDir
RETURNS: None
'''
def updateRepo( repoAddress, repoDir ):
    base = os.path.abspath(os.curdir)
    if not os.path.exists(repoDir):
        os.mkdir(repoDir)
        os.chdir(repoDir)
        subprocess.run(["git init"], shell = True)
        subprocess.run(["git remote add origin " + repoAddress], shell = True)
        subprocess.run(["git pull origin master"], shell = True)
    else:
        os.chdir(repoDir)
        subprocess.run(["git pull origin master"], shell = True)
    os.chdir(base)

# root and is relative to current file
'''
Build code with cmake function.
ARGUMENTS:
    - directory with sources
    (relatively to script path):
        root
    - target for executable
    (relatively to script path):
        target
RETURNS: None
'''
def build( root, target ):
    base = os.path.abspath(os.curdir)
    os.chdir(root)
    if not os.path.exists(target):
        os.mkdir(target)
    subprocess.run(["cmake -B " + target + " -G " + generatorCMakeParam], shell = True)
    os.chdir(target)
    subprocess.run([generator], shell = True)
    os.chdir(base)

'''
Edit CMakeLists file of student due to include tests function.
Includes testDir/CMakeLists.txt into the end of studentDir/CMakeLists.txt
ARGUMENTS: None
RETURNS: None
'''
def includeTests():
    base = os.path.abspath(os.curdir)
    cmakefile = open(studentDir + '/CMakeLists.txt', 'a')
    cmakefile.write('include(' + base + '/' + testDir + '/CMakeLists.txt)')
    cmakefile.close()

'''
stash changes in the test and student repo function.
ARGUMENTS: None
RETURNS: None
'''
def clear():
    base = os.path.abspath(os.curdir)
    os.chdir(studentDir)
    subprocess.run(["git stash"], shell = True)
    os.chdir(base + '/' + testDir)
    subprocess.run(["git stash"], shell = True)
    os.chdir(base)

'''
Run ctest function.
ARGUMENTS:
    - path to executable file
    (relatively to script path):
        pathToExecutable
    - log file name
    (relatively to path to exec):
        logName
RETURNS: None
'''
def runTest( pathToExecutable, logName ):
    base = os.path.abspath(os.curdir)
    os.chdir(pathToExecutable)
    subprocess.run(["ctest -O " + logName], shell = True)
    os.chdir(base)

'''
Parse log file function.
ARGUMENTS:
    - path to executable file
    (relatively to script path):
        pathToExecutable
    - log file name
    (relatively to path to exec):
        logName
RETURNS:
    list:
        1) dictionary: (test name -> pass status (True/False))
        2) list of nested exceptions 
'''
def parseLog( pathToExecutable, logName ):
    base = os.path.abspath(os.curdir)
    os.chdir(pathToExecutable)
    log = open(logName, 'rt')

    testNo = 1
    testRes = {}
    nestedException = []
    for string in log:
        found = string.find('Test #' + str(testNo))
        if found != -1:
            testNo += 1
            splittedStr = string.split()
            curTestName = splittedStr[3]

            if string.find('Passed') != -1:
                curTestRes = True
            else:
                curTestRes = False
                nestedException.append(''.join([splittedStr[i] + ' ' for i in range(5, len(splittedStr))]))
            testRes.update({curTestName: curTestRes})

    os.chdir(base)
    return [testRes, nestedException]

# parseRes == [testRes, nestedException]
'''
Generate output JSON file function.
ARGUMENTS:
    - file to output:
        fileName
    - parse result from `parseLog` function:
        parseRes
RETURNS: None
'''
def genJson( fileName, parseRes ):
    outJson = {"data": []}
    outF = open(fileName, 'wt')

    failMsgNum = 0
    for testRes in parseRes[0].items():
        str = {
            "packageName": packageName,
            "methodName": testRes[0],
            "tags": [],
            "results": [{
                "status": "SUCCESSFUL" if testRes[1] else "FAILED",
                "failure": {
                    "@class": "org.jetbrains.research.runner.data.UnknownFailureDatum",
                    "nestedException": parseRes[1][failMsgNum]
                } if not testRes[1] else None
            }]
        }
        failMsgNum += int(not testRes[1])
        outJson['data'].append(str)
    outF.write(json.dumps(outJson, indent = 4))
    outF.close()

'''
Main program function.
ARGUMENTS: None.
RETURNS:
    0 if success,
    1 if failed compilation.
'''
def main():
    updateRepo(testAddr, testDir)
    updateRepo(studentAddr, studentDir)
    includeTests()
    build(studentDir, buildDir)
    runTest(studentDir + '/' + buildDir, logName)
    parseRes = parseLog(studentDir + '/' + buildDir, logName)
    genJson(jsonFile, parseRes)
    clear()

main()
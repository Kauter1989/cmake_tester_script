import subprocess
import os
import json
import sys

'''
All paths here, excepting `buildDir` and logName,
are relative to script directory.
`buildDir` is relative to source code directory.
`logName` is relative to executable directory.
'''

base = ''

testAddr = 'https://github.com/Kauter1989/cmake_tester.git'
baseTestDir = 'test'
testDir = 'tests'
testingUtilDir = 'util'

studentDir = 'student'

buildDir = 'build'

generatorCMakeParam = 'Ninja'
generator = 'ninja'

packageName = 'lesson'

logName = 'log.txt'
jsonFile = 'results.json'

branch = 'master'


def run(command, sendException=True):
    status = subprocess.run([command], shell=True)
    if status.returncode != 0 and sendException:
        raise RuntimeError


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


def updateRepo(repoAddress, repoDir, revision=''):
    global base
    if not os.path.exists(repoDir):
        os.mkdir(repoDir)
        os.chdir(repoDir)
        run("git init")
        run("git remote add origin " + repoAddress)
    else:
        os.chdir(repoDir)
    run("git pull origin " + branch)
    run("git checkout " + revision)
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
RETURNS:
    return code of build
'''


def build(root, target):
    global base
    os.chdir(root)
    if not os.path.exists(target):
        os.mkdir(target)
    run("cmake -B " + target + " -G " + generatorCMakeParam)

    os.chdir(target)
    subprocess.run(generator)
    os.chdir(base)


'''
Edit CMakeLists file of student due to include tests function.
Includes testDir/CMakeLists.txt into the end of studentDir/CMakeLists.txt
ARGUMENTS: None
RETURNS: None
'''


def includeTests():
    global base
    cmakefile = open(baseTestDir + '/' + testingUtilDir + '/CMakeLists.txt', 'a')
    studcmakefile = open(studentDir + '/CMakeLists.txt', 'r')
    for s in studcmakefile:
        idx = s.find('project')
        if idx != -1:
            projname = s[idx + 8: s.find(')')]
            break
    cmakefile.write('set(STUDPROJNAME ' + projname + ')\n')
    cmakefile.write('include(' + base + '/' + baseTestDir + '/' + testDir + '/CMakeLists.txt)')
    studcmakefile.close()
    cmakefile.close()


'''
stash changes in the test and student repo function.
ARGUMENTS: None
RETURNS: None
'''


def clear():
    global base
    if os.path.exists(base + '/' + studentDir):
        os.chdir(base + '/' + studentDir)
        run("git stash")
    if os.path.exists(base + '/' + baseTestDir + '/' + testDir):
        os.chdir(base + '/' + baseTestDir + '/' + testDir)
        run("git stash")
    if os.path.exists(base + '/' + baseTestDir + '/' + testingUtilDir):
        os.chdir(base + '/' + baseTestDir + '/' + testingUtilDir)
        run("git stash")
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


def runTest(pathToExecutable, logName):
    global base
    os.chdir(pathToExecutable)
    run("ctest --output-on-failure -O " + logName, sendException=False)
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


def parseLog(pathToExecutable, logName, passedTestsCnt=-1):
    global base
    os.chdir(pathToExecutable)
    log = open(logName, 'rt')

    testNo = 1
    testRes = {}
    nestedException = []
    curTestRes = False
    foundTests = 0
    ready = False
    for string in log:
        found = string.find('Test #' + str(testNo))
        if found != -1:
            foundTests += 1
            testNo += 1
            splittedStr = string.split()
            curTestName = splittedStr[3]

            if string.find('Passed') != -1:
                curTestRes = True
                ready = foundTests == passedTestsCnt
            else:
                curTestRes = False

            testRes.update({curTestName: curTestRes})
        if curTestRes is False and string.upper().find('BAD') != -1:
            ready = foundTests == passedTestsCnt
            nestedException.append(string)
        if ready:
            break

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


def genJson(fileName, parseRes):
    global base
    outJson = {"data": []}
    outF = open(fileName, 'wt')

    failMsgNum = 0
    for testRes in parseRes[0].items():
        tagEndIdx = testRes[0].find('_')
        if tagEndIdx == -1:
            raise RuntimeError
        curTagName = testRes[0][0: tagEndIdx]
        curTestName = testRes[0][tagEndIdx + 1:]
        str = {
            "packageName": packageName,
            "methodName": curTestName,
            "tags": [curTagName],
            "results": [{
                "status": "SUCCESSFUL" if testRes[1] else "FAILED",
                "failure": {
                    "@class": "org.jetbrains.research.runner.data.UnknownFailureDatum",
                    "nestedException": parseRes[1][failMsgNum] if len(parseRes[1]) > failMsgNum else "No concrete error mentioned"
                } if not testRes[1] else None
            }]
        }
        failMsgNum += int(not testRes[1])
        outJson['data'].append(str)
    outF.write(json.dumps(outJson, indent=4))
    outF.close()


'''
Main program function.
ARGUMENTS: None.
RETURNS:
    0 if success,
    1 if failed compilation.
'''


def main():
    global base
    try:
        base = os.path.abspath(os.curdir)
        updateRepo(testAddr, baseTestDir)
        if "-src" not in sys.argv:
            raise RuntimeError
        studentAddr = sys.argv[sys.argv.index("-src") + 1]
        if "-v" in sys.argv:
            num = sys.argv.index("-v");
            updateRepo(studentAddr, studentDir, sys.argv[num + 1])
        else:
            updateRepo(studentAddr, studentDir)

        includeTests()
        build(studentDir, buildDir)
        build(baseTestDir + '/' + testingUtilDir, buildDir)
        runTest(baseTestDir + '/' + testingUtilDir + '/' + buildDir, logName)
        if "-tc" in sys.argv:
            num = sys.argv.index("-tc")
            passedTestCnt = int(sys.argv[num + 1])
            parseRes = parseLog(baseTestDir + '/' + testingUtilDir + '/' + buildDir,
                                logName, passedTestCnt)
        else:
            parseRes = parseLog(baseTestDir + '/' + testingUtilDir + '/' + buildDir,
                                logName)
        genJson(jsonFile, parseRes)
        clear()
    except:  # RuntimeError:
        print('Exception caught ')
        clear()
        run('rm -rf ' + base + '/' + studentDir + ' ' + base + '/' + baseTestDir)
        return 1
    return 0


main()

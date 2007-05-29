#! /usr/bin/env python

# @HEADER
# ************************************************************************
#
#                PyTrilinos: Python Interface to Trilinos
#                   Copyright (2005) Sandia Corporation
#
# Under terms of Contract DE-AC04-94AL85000, there is a non-exclusive
# license for use of this work by or on behalf of the U.S. Government.
#
# This library is free software; you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as
# published by the Free Software Foundation; either version 2.1 of the
# License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307
# USA
# Questions? Contact Michael A. Heroux (maherou@sandia.gov)
#
# ************************************************************************
# @HEADER

# Imports.  Users importing an installed version of PyTrilinos should use the
# "from PyTrilinos import ..." syntax.  Here, the setpath module adds the build
# directory, including "PyTrilinos", to the front of the search path.  We thus
# use "import ..." for Trilinos modules.  This prevents us from accidentally
# picking up a system-installed version and ensures that we are testing the
# build module.
from   numpy    import *
from   optparse import *
import sys
import unittest

parser = OptionParser()
parser.add_option("-b", "--use-boost", action="store_true", dest="boost",
                  default=False,
                  help="test the experimental boost-generated PyTrilinos package")
parser.add_option("-t", "--testharness", action="store_true",
                  dest="testharness", default=False,
                  help="test local build modules; prevent loading system-installed modules")
parser.add_option("-v", "--verbosity", type="int", dest="verbosity", default=2,
                  help="set the verbosity level [default 2]")
options,args = parser.parse_args()
if options.testharness:
    import setpath
    if options.boost: setpath.setpath("src-boost")
    else:             setpath.setpath()
    import Epetra
else:
    try:
        import setpath
        if options.boost: setpath.setpath("src-boost")
        else:             setpath.setpath()
        import Epetra
    except ImportError:
        from PyTrilinos import Epetra
        print >>sys.stderr, "Using system-installed Epetra"

##########################################################################

class EpetraImportTestCase(unittest.TestCase):
    "TestCase for Epetra_Import objects"

    # This test case tests Import objects for a transpose problem.  The global
    # problem is defined by a naturally-ordered NxN grid, where N = 2 * (# of
    # processors).  The source map is a column-wise 1D decomposition, and the
    # target map is a row-wise 1D decomposition.

    def setUp(self):
        self.comm       = Epetra.PyComm()
        self.numProc    = self.comm.NumProc()
        self.myPID      = self.comm.MyPID()
        self.myN        = 2
        self.globalN    = self.myN * self.numProc
        self.globalSize = self.globalN*self.globalN
        self.gids       = arange(self.globalSize,dtype='i')
        self.gids.shape = (self.globalN,self.globalN)
        self.start      = self.myN * self.myPID
        self.end        = self.start + self.myN
        self.trgMap     = Epetra.Map(-1,self.gids[:,self.start:self.end].ravel(),0,self.comm)
        self.srcMap     = Epetra.Map(-1,self.gids[self.start:self.end,:].ravel(),0,self.comm)
        self.importer   = Epetra.Import(self.trgMap, self.srcMap)
        self.numSameIDs = 0
        if self.myPID   == 0: self.numSameIDs = self.myN
        if self.numProc == 1: self.numSameIDs = self.myN * self.myN
        self.comm.Barrier()

    def tearDown(self):
        self.comm.Barrier()

    def testConstructors1(self):
        "Test Epetra.Import constructor"
        source = self.importer.SourceMap()
        target = self.importer.TargetMap()
        self.assertEqual(source.SameAs(self.srcMap), True)
        self.assertEqual(target.SameAs(self.trgMap), True)
        if self.numProc > 1:
            self.assertEqual(target.SameAs(source), False)

    def testConstructors2(self):
        "Test Epetra.Import copy constructor"
        importer = Epetra.Import(self.importer)
        source   = importer.SourceMap()
        target   = importer.TargetMap()
        self.assertEqual(source.SameAs(self.srcMap), True)
        self.assertEqual(target.SameAs(self.trgMap), True)
        if self.numProc > 1:
            self.assertEqual(target.SameAs(source), False)

    def testNumSameIDs(self):
        "Test Epetra.Import NumSameIDs method"
        self.assertEqual(self.importer.NumSameIDs(), self.numSameIDs)

    def testNumPermuteIDs(self):
        "Test Epetra.Import NumPermuteIDs method"
        numPermuteIDs = self.myN * self.myN - self.numSameIDs
        self.assertEqual(self.importer.NumPermuteIDs(), numPermuteIDs)

    def testPermuteFromLIDs(self):
        "Test Epetra.Import PermuteFromLIDs method"
        permuteFromGIDs = self.gids[self.start:self.end,self.start:self.end]
        if self.myPID == 0:
            permuteFromGIDs = permuteFromGIDs[1:,:]
        if self.numProc == 1:
            permuteFromGIDs = zeros((0,),"i")
        permuteFromGIDs = ravel(permuteFromGIDs)
        lists           = self.srcMap.RemoteIDList(permuteFromGIDs)
        permuteFromLIDs = lists[1]
        result          = self.importer.PermuteFromLIDs()
        self.assertEqual(len(result), len(permuteFromLIDs))
        for i in range(len(result)):
            self.assertEqual(result[i],permuteFromLIDs[i])

    def testPermuteToLIDs(self):
        "Test Epetra.Import PermuteToLIDs method"
        permuteToGIDs = self.gids[self.start:self.end,self.start:self.end]
        if self.myPID == 0:
            permuteToGIDs = permuteToGIDs[1:,:]
        if self.numProc == 1:
            permuteToGIDs = zeros((0,),"i")
        permuteToGIDs = ravel(permuteToGIDs)
        lists         = self.trgMap.RemoteIDList(permuteToGIDs)
        permuteToLIDs = lists[1]
        result        = self.importer.PermuteToLIDs()
        self.assertEqual(len(result), len(permuteToLIDs))
        for i in range(len(result)):
            self.assertEqual(result[i],permuteToLIDs[i])

    def testNumRemoteIDs(self):
        "Test Epetra.Import NumRemoteIDs method"
        numRemoteIDs  = self.myN * (self.globalN - self.myN)
        self.assertEqual(self.importer.NumRemoteIDs(), numRemoteIDs)

    def testRemoteLIDs(self):
        "Test Epetra.Import RemoteLIDs method"
        remoteGIDs = []
        for p in range(self.numProc):
            if p!= self.myPID:
                start = p * self.myN
                end   = start + self.myN
                remoteGIDs.extend(ravel(self.gids[start:end,self.start:self.end]))
        lists      = self.trgMap.RemoteIDList(remoteGIDs)
        remoteLIDs = lists[1]
        result     = self.importer.RemoteLIDs()
        self.assertEqual(len(result), len(remoteLIDs))
        # I've run into some situations where the result IDs are not ordered the
        # same way that I built the GID list
        for i in range(len(result)):
            self.assertEqual(result[i] in remoteLIDs, True)

    def testNumExportIDs(self):
        "Test Epetra.Import NumExportIDs method"
        numExportIDs  = self.myN * (self.globalN - self.myN)
        self.assertEqual(self.importer.NumExportIDs(), numExportIDs)

    def testExportLIDs(self):
        "Test Epetra.Import ExportLIDs method"
        exportGIDs = []
        for p in range(self.numProc):
            if p != self.myPID:
                start = p * self.myN
                end   = start + self.myN
                exportGIDs.extend(ravel(self.gids[self.start:self.end,start:end]))
        lists      = self.srcMap.RemoteIDList(exportGIDs)
        exportLIDs = lists[1]
        result     = self.importer.ExportLIDs()
        self.assertEqual(len(result), len(exportLIDs))
        for i in range(len(result)):
            self.assertEqual(result[i], exportLIDs[i])

    def testExportPIDs(self):
        "Test Epetra.Import ExportPIDs method"
        exportGIDs = []
        for p in range(self.numProc):
            if p != self.myPID:
                start = p * self.myN
                end   = start + self.myN
                exportGIDs.extend(ravel(self.gids[self.start:self.end,start:end]))
        lists      = self.trgMap.RemoteIDList(exportGIDs)
        exportPIDs = lists[0]
        result     = self.importer.ExportPIDs()
        self.assertEqual(len(result), len(exportPIDs))
        for i in range(len(result)):
            self.assertEqual(result[i], exportPIDs[i])

    def testNumSend(self):
        "Test Epetra.Import NumSend method"
        numSend  = self.myN * (self.globalN - self.myN)
        self.assertEqual(self.importer.NumSend(), 0)

    def testNumRecv(self):
        "Test Epetra.Import NumRecv method"
        numRecv  = self.myN * (self.globalN - self.myN)
        self.assertEqual(self.importer.NumRecv(), numRecv)

    def testSourceMap(self):
        "Test Epetra.Import SourceMap method"
        source = self.importer.SourceMap()
        self.assertEqual(source.SameAs(self.srcMap), True)

    def testTargetMap(self):
        "Test Epetra.Import TargetMap method"
        target = self.importer.TargetMap()
        self.assertEqual(target.SameAs(self.trgMap), True)

    def testPrint(self):
        "Test Epetra.Import Print method"
        filename = "testImportExport%d.dat" % self.myPID
        f = open(filename,"w")
        self.importer.Print(f)
        f.close()
        s = open(filename,"r").readlines()
        lines = 42 + 2*self.myN*self.myN*self.numProc
        if self.myPID == 0: lines += 14
        if self.numProc == 1: lines -= 10
        self.assertEquals(len(s),lines)

    def testStr(self):
        "Test Epetra.Import __str__ method"
        s = str(self.importer)
        s = s.splitlines()
        lines = 42 + 2*self.myN*self.myN*self.numProc
        if self.myPID == 0: lines += 14
        if self.numProc == 1: lines -= 10
        self.assertEquals(len(s),lines)

##########################################################################

class EpetraExportTestCase(unittest.TestCase):
    "TestCase for Epetra_Export objects"

    # This test case tests Export objects for a transpose problem.  The global
    # problem is defined by a naturally-ordered NxN grid, where N = 2 * (# of
    # processors).  The source map is a column-wise 1D decomposition, and the
    # target map is a row-wise 1D decomposition.

    def setUp(self):
        self.comm       = Epetra.PyComm()
        self.numProc    = self.comm.NumProc()
        self.myPID      = self.comm.MyPID()
        self.myN        = 2
        self.globalN    = self.myN * self.numProc
        self.globalSize = self.globalN*self.globalN
        self.gids       = arange(self.globalSize,dtype='i')
        self.gids.shape = (self.globalN,self.globalN)
        self.start      = self.myN * self.myPID
        self.end        = self.start + self.myN
        self.trgMap     = Epetra.Map(-1,self.gids[:,self.start:self.end].ravel(),0,self.comm)
        self.srcMap     = Epetra.Map(-1,self.gids[self.start:self.end,:].ravel(),0,self.comm)
        self.exporter   = Epetra.Export(self.srcMap, self.trgMap)
        self.numSameIDs = 0
        if self.myPID   == 0: self.numSameIDs = self.myN
        if self.numProc == 1: self.numSameIDs = self.myN * self.myN
        self.comm.Barrier()

    def tearDown(self):
        self.comm.Barrier()

    def testConstructors1(self):
        "Test Epetra.Export constructor"
        source = self.exporter.SourceMap()
        target = self.exporter.TargetMap()
        self.assertEqual(source.SameAs(self.srcMap), True)
        self.assertEqual(target.SameAs(self.trgMap), True)
        if self.numProc > 1:
            self.assertEqual(target.SameAs(source), False)

    def testConstructors2(self):
        "Test Epetra.Export copy constructor"
        exporter = Epetra.Export(self.exporter)
        source   = exporter.SourceMap()
        target   = exporter.TargetMap()
        self.assertEqual(source.SameAs(self.srcMap), True)
        self.assertEqual(target.SameAs(self.trgMap), True)
        if self.numProc > 1:
            self.assertEqual(target.SameAs(source), False)

    def testNumSameIDs(self):
        "Test Epetra.Export NumSameIDs method"
        self.assertEqual(self.exporter.NumSameIDs(), self.numSameIDs)

    def testNumPermuteIDs(self):
        "Test Epetra.Export NumPermuteIDs method"
        numPermuteIDs = self.myN * self.myN - self.numSameIDs
        self.assertEqual(self.exporter.NumPermuteIDs(), numPermuteIDs)

    def testPermuteFromLIDs(self):
        "Test Epetra.Export PermuteFromLIDs method"
        permuteFromGIDs = self.gids[self.start:self.end,self.start:self.end]
        if self.myPID == 0:
            permuteFromGIDs = permuteFromGIDs[1:,:]
        if self.numProc == 1:
            permuteFromGIDs = zeros((0,),"i")
        permuteFromGIDs = ravel(permuteFromGIDs)
        lists           = self.srcMap.RemoteIDList(permuteFromGIDs)
        permuteFromLIDs = lists[1]
        result = self.exporter.PermuteFromLIDs()
        self.assertEqual(len(result), len(permuteFromLIDs))
        for i in range(len(result)):
            self.assertEqual(result[i],permuteFromLIDs[i])

    def testPermuteToLIDs(self):
        "Test Epetra.Export PermuteToLIDs method"
        permuteToGIDs = self.gids[self.start:self.end,self.start:self.end]
        if self.myPID == 0:
            permuteToGIDs = permuteToGIDs[1:,:]
        if self.numProc == 1:
            permuteToGIDs = zeros((0,),"i")
        permuteToGIDs = ravel(permuteToGIDs)
        lists         = self.trgMap.RemoteIDList(permuteToGIDs)
        permuteToLIDs = lists[1]
        result = self.exporter.PermuteToLIDs()
        self.assertEqual(len(result), len(permuteToLIDs))
        for i in range(len(result)):
            self.assertEqual(result[i],permuteToLIDs[i])

    def testNumRemoteIDs(self):
        "Test Epetra.Export NumRemoteIDs method"
        numRemoteIDs  = self.myN * (self.globalN - self.myN)
        self.assertEqual(self.exporter.NumRemoteIDs(), numRemoteIDs)

    def testRemoteLIDs(self):
        "Test Epetra.Export RemoteLIDs method"
        remoteGIDs = []
        for p in range(self.numProc):
            if p!= self.myPID:
                start = p * self.myN
                end   = start + self.myN
                remoteGIDs.extend(ravel(self.gids[start:end,self.start:self.end]))
        lists      = self.trgMap.RemoteIDList(remoteGIDs)
        remoteLIDs = lists[1]
        result = self.exporter.RemoteLIDs()
        self.assertEqual(len(result), len(remoteLIDs))
        # I've run into some situations where the result IDs are not ordered the
        # same way that I built the GID list
        for i in range(len(result)):
            self.assertEqual(result[i] in remoteLIDs, True)

    def testNumExportIDs(self):
        "Test Epetra.Export NumExportIDs method"
        numExportIDs  = self.myN * (self.globalN - self.myN)
        self.assertEqual(self.exporter.NumExportIDs(), numExportIDs)

    def testExportLIDs(self):
        "Test Epetra.Export ExportLIDs method"
        exportGIDs = []
        for p in range(self.numProc):
            if p != self.myPID:
                start = p * self.myN
                end   = start + self.myN
                exportGIDs.extend(ravel(self.gids[self.start:self.end,start:end]))
        lists      = self.srcMap.RemoteIDList(exportGIDs)
        exportLIDs = lists[1]
        result     = self.exporter.ExportLIDs()
        self.assertEqual(len(result), len(exportLIDs))
        # I've run into some situations where the result IDs are not ordered the
        # same way that I built the GID list
        for i in range(len(result)):
            self.assertEqual(result[i] in exportLIDs, True)

    def testExportPIDs(self):
        "Test Epetra.Export ExportPIDs method"
        exportGIDs = []
        for p in range(self.numProc):
            if p != self.myPID:
                start = p * self.myN
                end   = start + self.myN
                exportGIDs.extend(ravel(self.gids[self.start:self.end,start:end]))
        lists      = self.trgMap.RemoteIDList(exportGIDs)
        exportPIDs = lists[0]
        result     = self.exporter.ExportPIDs()
        self.assertEqual(len(result), len(exportPIDs))
        for i in range(len(result)):
            self.assertEqual(result[i], exportPIDs[i])

    def testNumSend(self):
        "Test Epetra.Export NumSend method"
        numSend  = self.myN * (self.globalN - self.myN)
        self.assertEqual(self.exporter.NumSend(), numSend)

    def testNumRecv(self):
        "Test Epetra.Export NumRecv method"
        numRecv  = self.myN * (self.globalN - self.myN)
        self.assertEqual(self.exporter.NumRecv(), numRecv)

    def testSourceMap(self):
        "Test Epetra.Export SourceMap method"
        source = self.exporter.SourceMap()
        self.assertEqual(source.SameAs(self.srcMap), True)

    def testTargetMap(self):
        "Test Epetra.Export TargetMap method"
        target = self.exporter.TargetMap()
        self.assertEqual(target.SameAs(self.trgMap), True)

    def testPrint(self):
        "Test Epetra.Export Print method"
        filename = "testImportExport%d.dat" % self.myPID
        f = open(filename,"w")
        self.exporter.Print(f)
        f.close()
        s = open(filename,"r").readlines()
        lines = 41 + 2*self.myN*self.myN*self.numProc
        if self.myPID == 0: lines += 14
        if self.numProc == 1: lines -= 10
        self.assertEquals(len(s),lines)

    def testStr(self):
        "Test Epetra.Export __str__ method"
        s = str(self.exporter)
        s = s.splitlines()
        lines = 41 + 2*self.myN*self.myN*self.numProc
        if self.myPID == 0: lines += 14
        if self.numProc == 1: lines -= 10
        self.assertEquals(len(s),lines)

##########################################################################

if __name__ == "__main__":

    # Create the test suite object
    suite = unittest.TestSuite()

    # Add the test cases to the test suite
    suite.addTest(unittest.makeSuite(EpetraImportTestCase))
    suite.addTest(unittest.makeSuite(EpetraExportTestCase))

    # Create a communicator
    comm    = Epetra.PyComm()
    iAmRoot = comm.MyPID() == 0

    # Run the test suite
    if iAmRoot: print >>sys.stderr, \
          "\n****************************\nTesting Epetra.Import/Export\n" + \
          "****************************\n"
    verbosity = options.verbosity * int(iAmRoot)
    result = unittest.TextTestRunner(verbosity=verbosity).run(suite)

    # Exit with a code that indicates the total number of errors and failures
    errsPlusFails = comm.SumAll(len(result.errors) + len(result.failures))
    if errsPlusFails == 0 and iAmRoot: print "End Result: TEST PASSED"
    sys.exit(errsPlusFails)

# Draw after-burner boundary lines in tecplot 
import tecplot as tp
from tecplot.constant import *
import sys
import os
import glob
import numpy as np
from shapely.geometry import Point
from shapely.geometry.polygon import Polygon


def getPolygon(frame):
    pts = []

    for geom in frame.geometries():
        if "Circle" in str(type(geom)):
            # Get location
            p = geom.position
            pts.append(
                    (p[0],p[1])
                    )
    return Polygon(pts)

def hidePolygon(frame):
    # Hide the circles save it to the original layout file
    for geom in frame.geometries():
        if "Circle" in str(type(geom)):
            # Set them draw 
            geom.draw_order = DrawOrder.BeforeData
            geom.color = Color.White


def showPolygon(frame):
    # Show the circles
    for geom in frame.geometries():
        if "Circle" in str(type(geom)):
            # Set them draw 
            geom.draw_order = DrawOrder.AfterData
            geom.color = Color.Black
            geom.line_thickness = 0.5

def process(layFile, caseDir):

    # connect with tecplot
    tp.session.connect(port=7600)
    tp.load_layout(layFile)
    frame = tp.active_frame()
    showPolygon(frame)
    
    # 1. First draw circles to specify the region
    #  we want to handle
    input("1. I'm waiting for you to draw circles...[Y/n]")
    
    polygon = getPolygon(frame)

    # 2. Save the layout file
    
    hidePolygon(frame)
    tp.save_layout(layFile, use_relative_paths=True)
    showPolygon(frame)
    tp.session.disconnect()
    
    # Read PIV-new.dat and do interpolation
    pivDataFile = caseDir+"/PIV-new.dat"
    data = np.genfromtxt(pivDataFile, skip_header=5)
    
    with open(pivDataFile,'r') as f:
        lines = f.readlines()
        header = lines[0:5]
    
    imax = int(lines[3].split()[1])
    jmax = int(lines[3].split()[4])
    
    x = data[:,0]
    y = data[:,1]
    nPoints = len(x)

    indI = np.zeros((jmax,2),dtype=int)

    # Get left and right boundary 
    for j in range(jmax):
        pInPoly = []
        for i in range(imax):
            n = i+j*imax
            p = Point(x[n], y[n])
            if polygon.contains(p):
                pInPoly.append(True)
            else:
                pInPoly.append(False)

        for i in range(imax-1):
            if pInPoly[i] == False and pInPoly[i+1] == True:
                indI[j,0] = i
            elif pInPoly[i] == True and pInPoly[i+1] == False:
                indI[j,1] = i
                break

    for j in range(jmax):
        for i in range(imax):
            n = i+j*imax
            p = Point(x[n], y[n])
            if polygon.contains(p):
                # Now we do interpolation
                i1 = indI[j,0]
                i2 = indI[j,1]
                n1 = i1+j*imax
                n2 = i2+j*imax
                for k in range(3,13):
                    # Fix
                    # data[n,k] = 86
                    # Central
                    #data[n,k] = 0.5*(data[n1,k]+data[n2,k])
                    # Linear
                    alpha = (x[n]-x[n1])/(x[n2]-x[n1])
                    data[n,k] = alpha*(data[n2,k]-data[n1,k])+data[n1,k]

    tecNewFile = pivDataFile.replace(".dat","-mod.dat")
    with open(tecNewFile,'w') as f:
        f.writelines(header)
        for n in range(nPoints):
            line = ''
            for i in range(len(data[n,:])):
                line += str(data[n,i])+'\t'
            line += '\n'
            f.write(line)
        # Write Polygon to the data file
        f.write("\n")
        f.write("# Polygon Points\n")
        f.write(str(polygon))

    tp.session.connect(port=7601)
    tp.load_layout(layFile)
    tp.data.load_tecplot(tecNewFile, read_data_option=ReadDataOption.Replace, reset_style=False)
    newLayFile = layFile.replace(".lay","-mod.lay")
    tp.save_layout(newLayFile,use_relative_paths=True)
    frameNew = tp.active_frame()
    imgFile = newLayFile.replace(".lay",".png")
    tp.save_png(imgFile)
    tp.session.disconnect()

    userInput = input("2. Next case data? [y]/n:") or "y"

    return userInput
    


def main():
    '''
    # jizhunjian 12.19
    dirs = [
            "duanzhiban",
            "zhongjianjiemian"
            ]
    pattern = "/*[ng].lay"
    '''
    '''
    # youhua-1 18du 
    dirs = [
            "duanzhiban",
            "yinsheqi-18du"
            ]
    pattern = "/*[nq].lay"
    '''
    '''
    # youhua-1 28du
    dirs = [
            "duanzhiban",
            "yinsheqi"
            ]
    pattern = "/*[nqe].lay"
    '''
    # youhua-1 28du
    dirs = [
            "duanzhiban",
            "yinsheqi"
            ]
    pattern = "/*[nq].lay"

    for dir in dirs:
        for caseDir in os.listdir(dir):
            caseDir = dir+"/"+caseDir
            print(caseDir)
            if os.path.isdir(caseDir):
                for layFile in glob.glob(caseDir+pattern):
                    userInput = "n"
                    while(userInput != "y"):
                        print("Processing: ",layFile)
                        userInput = process(layFile, caseDir)
                        print(userInput)

if __name__ == "__main__":
    main()

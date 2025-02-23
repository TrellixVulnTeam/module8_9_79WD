# Import module ________________________________________________________________________________________________________
import time
import math
import ast
import cv2

# Import class _________________________________________________________________________________________________________
from Dynamixel import *
from Bord import *
from RealtimePredict import *
from blr import *
from Get_Position import *
from Planning import PathPlan

class Main:

    class Const:
        # Const. Position
        Homei = [180, 70, 30, 90, 60, 90]
        Home = [180, 90, 30, 90, 60, 90]

        Front = [5, 80, 30, 90, 60, 90]  ##
        Right = [90, 80, 30, 90, 60, 90]

        # Variable _____________________________________________________________________________________________________
        CameraRight = [[-50, -70],
                       [90, -30], [90, -10], [90, 10], [90, 25],
                       [75, 22], [70, 10], [70, 0], [70, -10], [70, -20],
                       [60, -20], [60, -10], [55, 0], [55, 10], [55, 20], [55, 25]]

        CameraBase = [[-35, -50], [-17, -60], [0, -59], [17, -60], [35, -50]]

        CameraLeft = [[-70, 22], [-70, 0], [-60, 0], [-60, 10], [-60, -10], [-60, -20],
                      [-70, -20], [-70, -10], [-70, 0], [-70, 10], [-75, 22],
                      [-90, 25], [-90, 10], [-90, -10], [-90, -30]]


    def __init__(self,nomodeset=0):
        # Call class ___________________________________________________________________________________________________
        if nomodeset == 1:
            self.KHONG = Board('COM7',115200)
        elif nomodeset == 2:
            self.CAMER = Dynamixel('COM3',1000000)
        elif nomodeset == 0:
            self.KHONG = Board('COM7',115200)
            self.CAMER = Dynamixel('COM3',1000000)
        else:
            raise NameError('NoMode not found (your mode is ',nomodeset)

        # homo = Get_Position.homo
        self.rtp = Real_Time_Predict()
        # self.rtp.create_camera_instance(0)
        self.rtp.create_HogDescriptor()

        self.convert = Get_Position.World()
        self.newcammtx = Get_Position.newcammtx


    # Function _________________________________________________________________________________________________________
    def camera(self,pantilt):
        self.CAMER.PAN(pantilt[0])
        self.CAMER.TILT(pantilt[1])
        self.CAMER.WaitFinish([1,9])

    def cmKhong(self,position):
        self.KHONG.SetPosition(position)
        time.sleep(0.1)
        #KHONG.WaitFinish()

    def cam_clf(self, DATA_PACK, brl, pt):

        self.rtp.create_camera_instance(0)

        # open camera and read model and predict get centroid of picture and 4 points of conner
        cardlist, midpointlist, cornerlist, realworldlist = self.rtp.one_time()

        # get_homo, put pantile's list by pan is q1 and tilt is q2 , blr is scene ('l', 'r', 'blbr')
        homo = blr.get_homo(q1_=pt[0], q2_=pt[1], blr_=brl)

        # realworldlist is the function that convert centroid of picture to centroid of picture with respect to world coordinate
        realworldlist = convert_pos(midpointlist, newcammtx, homo)

        # same as realworldlist but it using 4 points of conner
        cornerworldlist = convert_pos(cornerlist, newcammtx, homo, mode=0, inverse=False)

        # data_pack include 1.cardlist is class og each card, 2.midpointlist is useless, 3.cornerworldlist is cornerworldlist
        #                   4.realworldlist is realworldlist, 5.data_pack (it will send to MATLAB later) 6.parameter that tell scene
        data_pack = pack_data(cardlist, midpointlist, cornerworldlist, realworldlist, DATA_PACK, brl)
        self.rtp.release_camera_instance()

        print(data_pack)
        return data_pack

    def transform_angle(self,q_configuration):
        q_homeconfig = [180,90,30,90,60,90]
        q_symbol = [-1,-1,1,-1,1,-1]
        q_transform = []
        for i in range(0,6):
            q_transform.append(q_homeconfig[i] + q_symbol[i]*q_configuration[i])
        return q_transform

    # Loop camera(pan,tilt),classify, position _________________________________________________________________________
    def Step1FindCard(self):
        T_CLF = time.time()
        STATE = 1
        CARD_POSITION = []

        for PT in Main.Const.CameraRight:
            if STATE == 1:
                # 1. Rotate J1 90 degree
                #self.cmKhong(Main.Const.Right)
                # 2. Pan CAM (-50,-70)
                #self.camera(PT)
                # 3. Predict & Position
                #CARD_POSITION = self.cam_clf(CARD_POSITION,'br',PT)
                pass

            else:
                # 4. Rotate J1 90 degree
                if STATE == 2:
                    self.cmKhong(Main.Const.Front)
                    time.sleep(8)
                # 5. Pan CAM [95,-30],[95,-10],[95,15],[95,22],[70,22],[70,-10],[70,-30]
                self.camera(PT)
                # 6. Predict & Position
                CARD_POSITION = self.cam_clf(CARD_POSITION,'r',PT)
            STATE += 1

        for PT in Main.Const.CameraBase:
            self.camera(PT)
            CARD_POSITION = self.cam_clf(CARD_POSITION,'b',PT)

        for PT in Main.Const.CameraLeft:
            if STATE != 16:
                # 7. Pan CAM [-95,-30],[-95,-10],[-95,15],[-95,22],[-70,22],[-70,-10],[-70,-30]
                self.camera(PT)
                # 8. Predict & Position
                CARD_POSITION = self.cam_clf(CARD_POSITION,'l',PT)
            else:
################# Can't rotate Joint 1 to -90 degree ###################################################################
                # 9. Rotate J1 90 degree
                #self.cmKhong()
                # 10. Pan CAM
                #self.camera(PT)
                # 11. Predict & Position
                #CARD_POSITION = self.cam_clf(CARD_POSITION,'bl',PT)
                pass
            STATE += 1

        # Set home position
        self.CAMER.PANTILT(0)
        self.cmKhong(Main.Const.Homei)
        time.sleep(8)
        self.cmKhong(Main.Const.Home)
        ENDT_CLF = time.time() - T_CLF
        cv2.destroyAllWindows()
        return CARD_POSITION, ENDT_CLF

# Planning (MATLAB) ____________________________________________________________________________________________________
    def Step2PathPlan(self,CardPosition):
        T_PLN = time.time()
        CHIN = PathPlan(CardPosition)
        PATH = CHIN.EvaluateTraject()
        ENDT_PLN = time.time() - T_PLN
        return PATH,ENDT_PLN

# Command Khong ________________________________________________________________________________________________________
    def Step3CommandKhong(self,PATH):
        T_LLV = time.time()
        temp = 0
        #Traject
        pose = [180,90,30,90,90,60]
        manual = [[119, -13, 66, -78, 59, 77], [100, -5, 55, -47, 44, 46],
                  [76, -6, 56, 56, 47, -55], [56, -15, 69, 81, 65, -79],
                  [119, -19, 47, -45, 73, 36], [100, -12, 35, -17, 68, 14],
                  [76, -13, 35, 21, 70, -17], [58, -16, 45, 50, 74, -41]]
        old_pose = [90,60,90]
        for path in range(len(PATH)):
            #Sub Traject
            for STpath in range(len(PATH[path])):
                via = PATH[path][STpath][len(PATH[path][STpath])-1]
                for k in range(len(PATH[path][STpath])):
                    pose = [0,0,0,0,0,0]
                    pose[3:6] = old_pose
                    tj = PATH[path][STpath][k]
                    if k != len(PATH[path][STpath])-1:
                        pose[0:3] = tj[0:3]
                    else:
                        pose = via
                    old_pose = pose[3:6]
                    self.cmKhong(pose)
                    print('via: ',pose)
            if (path+1)%2 ==0:
                if (path+1)%4 == 0:
                    time.sleep(3)
                    #manual[temp][5] = via[5]
                    self.cmKhong(self.transform_angle(manual[temp]))
                    time.sleep(1.5)
                    self.KHONG.SetGrip(0)
                    temp += 1
                else:
                    self.KHONG.SetGrip(1)

            print('Finish SUB ',path)
            time.sleep(2)

        self.KHONG.SetGrip(0)
        ENDT_LLV = time.time() - T_LLV
        return ENDT_LLV

if __name__ == '__main__':
    Sequen = Main(nomodeset=0)
    CardPosition, T_1 = Sequen.Step1FindCard()
    #print(CardPosition)
    #CardPosition = [[[600.,510.,500.],[3.14/2,-3.14/2,3.14],0.],
    #                [[600.,-478.,800.],[3.14/2,-3.14/2,0.],13.]]
    #Path = open('path.txt','r').read()
    #Path = ast.literal_eval(Path)
    Path, T_2 = Sequen.Step2PathPlan(CardPosition)
    T_3 = Sequen.Step3CommandKhong(Path)

# In Conclusion ________________________________________________________________________________________________________
    print('Summary')
    print('1. Time for find card: ',T_1)
    print('2. Time for Planning : ',T_2)
    print('3. Time for Running  : ',T_3)
    print('4. Time All  : ', (T_1+T_2+T_3),' s')

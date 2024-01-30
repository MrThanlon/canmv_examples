import aicube                   #aicube模块，封装检测分割等任务相关后处理
from media.camera import *      #摄像头模块
from media.display import *     #显示模块
from media.media import *       #软件抽象模块，主要封装媒体数据链路以及媒体缓冲区

import nncase_runtime as nn     #nncase运行模块，封装了kpu（kmodel推理）和ai2d（图片预处理加速）操作
import ulab.numpy as np         #类似python numpy操作，但也会有一些接口不同

import time                     #时间统计
import image                    #图像模块，主要用于读取、图像绘制元素（框、点等）等操作

import gc                       #垃圾回收模块
import os, sys                  #操作系统接口模块

##config.py
#display分辨率
DISPLAY_WIDTH = ALIGN_UP(1920, 16)
DISPLAY_HEIGHT = 1080

##ai原图分辨率输入
OUT_RGB888P_WIDTH = ALIGN_UP(1920, 16)
OUT_RGB888P_HEIGHT = 1080

root_dir = '/sdcard/app/tests/'

#--------for hand detection----------
#kmodel输入shape
hd_kmodel_input_shape = (1,3,512,512)                               # 手掌检测kmodel输入分辨率

#kmodel相关参数设置
confidence_threshold = 0.2                                          # 手掌检测阈值，用于过滤roi
nms_threshold = 0.5                                                 # 手掌检测框阈值，用于过滤重复roi
hd_kmodel_frame_size = [512,512]                                    # 手掌检测输入图片尺寸
hd_frame_size = [OUT_RGB888P_WIDTH,OUT_RGB888P_HEIGHT]              # 手掌检测直接输入图片尺寸
strides = [8,16,32]                                                 # 输出特征图的尺寸与输入图片尺寸的比
num_classes = 1                                                     # 手掌检测模型输出类别数
nms_option = False                                                  # 是否所有检测框一起做NMS，False则按照不同的类分别应用NMS

hd_kmodel_file = root_dir + 'kmodel/hand_det.kmodel'                # 手掌检测kmodel文件的路径
anchors = [26,27, 53,52, 75,71, 80,99, 106,82, 99,134, 140,113, 161,172, 245,276]   #anchor设置

#--------for hand keypoint detection----------
#kmodel输入shape
hk_kmodel_input_shape = (1,3,256,256)                               # 手掌关键点检测kmodel输入分辨率

#kmodel相关参数设置
hk_kmodel_frame_size = [256,256]                                    # 手掌关键点检测输入图片尺寸
hk_kmodel_file = root_dir + 'kmodel/handkp_det.kmodel'              # 手掌关键点检测kmodel文件的路径

#--------for hand gesture----------
#kmodel输入shape
gesture_kmodel_input_shape = [[1, 3, 224, 224],                     # 动态手势识别kmodel输入分辨率
                            [1,3,56,56],
                            [1,4,28,28],
                            [1,4,28,28],
                            [1,8,14,14],
                            [1,8,14,14],
                            [1,8,14,14],
                            [1,12,14,14],
                            [1,12,14,14],
                            [1,20,7,7],
                            [1,20,7,7]]

#kmodel相关参数设置
resize_shape = 256
mean_values = np.array([0.485, 0.456, 0.406]).reshape((3,1,1))      # 动态手势识别预处理均值
std_values = np.array([0.229, 0.224, 0.225]).reshape((3,1,1))       # 动态手势识别预处理方差
gesture_kmodel_frame_size = [224,224]                               # 动态手势识别输入图片尺寸

gesture_kmodel_file = root_dir + 'kmodel/gesture.kmodel'            # 动态手势识别kmodel文件的路径

shang_bin = root_dir + "utils/shang.bin"                            # 动态手势识别屏幕坐上角标志状态文件的路径
xia_bin = root_dir + "utils/xia.bin"                                # 动态手势识别屏幕坐上角标志状态文件的路径
zuo_bin = root_dir + "utils/zuo.bin"                                # 动态手势识别屏幕坐上角标志状态文件的路径
you_bin = root_dir + "utils/you.bin"                                # 动态手势识别屏幕坐上角标志状态文件的路径

bin_width = 150                                                     # 动态手势识别屏幕坐上角标志状态文件的短边尺寸
bin_height = 216                                                    # 动态手势识别屏幕坐上角标志状态文件的长边尺寸
shang_argb = np.fromfile(shang_bin, dtype=np.uint8)
shang_argb = shang_argb.reshape((bin_height, bin_width, 4))
xia_argb = np.fromfile(xia_bin, dtype=np.uint8)
xia_argb = xia_argb.reshape((bin_height, bin_width, 4))
zuo_argb = np.fromfile(zuo_bin, dtype=np.uint8)
zuo_argb = zuo_argb.reshape((bin_width, bin_height, 4))
you_argb = np.fromfile(you_bin, dtype=np.uint8)
you_argb = you_argb.reshape((bin_width, bin_height, 4))

TRIGGER = 0                                                         # 动态手势识别应用的结果状态
MIDDLE = 1
UP = 2
DOWN = 3
LEFT = 4
RIGHT = 5

max_hist_len = 20                                                   # 最多存储多少帧的结果

debug_mode = 0                                                      # debug模式 大于0（调试）、 反之 （不调试）

#scoped_timing.py 用于debug模式输出程序块运行时间
class ScopedTiming:
    def __init__(self, info="", enable_profile=True):
        self.info = info
        self.enable_profile = enable_profile

    def __enter__(self):
        if self.enable_profile:
            self.start_time = time.time_ns()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if self.enable_profile:
            elapsed_time = time.time_ns() - self.start_time
            print(f"{self.info} took {elapsed_time / 1000000:.2f} ms")

#ai_utils.py
global current_kmodel_obj                                                                                                     # 定义全局的 kpu 对象
global hd_ai2d,hd_ai2d_input_tensor,hd_ai2d_output_tensor,hd_ai2d_builder                                                     # 定义手掌检测全局 ai2d 对象，并且定义 ai2d 的输入、输出 以及 builder
global hk_ai2d,hk_ai2d_input_tensor,hk_ai2d_output_tensor,hk_ai2d_builder                                                     # 定义手掌关键点检测全局 ai2d 对象，并且定义 ai2d 的输入、输出 以及 builder
global gesture_ai2d_resize, gesture_ai2d_resize_builder, gesture_ai2d_crop, gesture_ai2d_crop_builder                         # 定义动态手势识别全局 ai2d 对象，以及 builder
global gesture_ai2d_input_tensor, gesture_kpu_input_tensors, gesture_ai2d_middle_output_tensor, gesture_ai2d_output_tensor    # 定义动态手势识别全局 ai2d 的输入、输出

#-------hand detect--------:
# 手掌检测ai2d 初始化
def hd_ai2d_init():
    with ScopedTiming("hd_ai2d_init",debug_mode > 0):
        global hd_ai2d
        global hd_ai2d_builder
        global hd_ai2d_output_tensor
        # 计算padding值
        ori_w = OUT_RGB888P_WIDTH
        ori_h = OUT_RGB888P_HEIGHT
        width = hd_kmodel_frame_size[0]
        height = hd_kmodel_frame_size[1]
        ratiow = float(width) / ori_w
        ratioh = float(height) / ori_h
        if ratiow < ratioh:
            ratio = ratiow
        else:
            ratio = ratioh
        new_w = int(ratio * ori_w)
        new_h = int(ratio * ori_h)
        dw = float(width - new_w) / 2
        dh = float(height - new_h) / 2
        top = int(round(dh - 0.1))
        bottom = int(round(dh + 0.1))
        left = int(round(dw - 0.1))
        right = int(round(dw - 0.1))

        hd_ai2d = nn.ai2d()
        hd_ai2d.set_dtype(nn.ai2d_format.NCHW_FMT,
                                       nn.ai2d_format.NCHW_FMT,
                                       np.uint8, np.uint8)
        hd_ai2d.set_pad_param(True, [0,0,0,0,top,bottom,left,right], 0, [114,114,114])
        hd_ai2d.set_resize_param(True, nn.interp_method.tf_bilinear, nn.interp_mode.half_pixel )
        hd_ai2d_builder = hd_ai2d.build([1,3,OUT_RGB888P_HEIGHT,OUT_RGB888P_WIDTH], [1,3,height,width])

        data = np.ones(hd_kmodel_input_shape, dtype=np.uint8)
        hd_ai2d_output_tensor = nn.from_numpy(data)

# 手掌检测 ai2d 运行
def hd_ai2d_run(rgb888p_img):
    with ScopedTiming("hd_ai2d_run",debug_mode > 0):
        global hd_ai2d_input_tensor,hd_ai2d_output_tensor, hd_ai2d_builder
        hd_ai2d_input = rgb888p_img.to_numpy_ref()
        hd_ai2d_input_tensor = nn.from_numpy(hd_ai2d_input)

        hd_ai2d_builder.run(hd_ai2d_input_tensor, hd_ai2d_output_tensor)

# 手掌检测 ai2d 释放内存
def hd_ai2d_release():
    with ScopedTiming("hd_ai2d_release",debug_mode > 0):
        global hd_ai2d_input_tensor
        del hd_ai2d_input_tensor

# 手掌检测 kpu 初始化
def hd_kpu_init(hd_kmodel_file):
    # init kpu and load kmodel
    with ScopedTiming("hd_kpu_init",debug_mode > 0):
        hd_kpu_obj = nn.kpu()
        hd_kpu_obj.load_kmodel(hd_kmodel_file)

        hd_ai2d_init()
        return hd_kpu_obj

# 手掌检测 kpu 输入预处理
def hd_kpu_pre_process(rgb888p_img):
    hd_ai2d_run(rgb888p_img)
    with ScopedTiming("hd_kpu_pre_process",debug_mode > 0):
        global current_kmodel_obj,hd_ai2d_output_tensor
        # set kpu input
        current_kmodel_obj.set_input_tensor(0, hd_ai2d_output_tensor)

# 手掌检测 kpu 获得 kmodel 输出
def hd_kpu_get_output():
    with ScopedTiming("hd_kpu_get_output",debug_mode > 0):
        global current_kmodel_obj
        results = []
        for i in range(current_kmodel_obj.outputs_size()):
            data = current_kmodel_obj.get_output_tensor(i)
            result = data.to_numpy()
            result = result.reshape((result.shape[0]*result.shape[1]*result.shape[2]*result.shape[3]))
            tmp2 = result.copy()
            del result
            results.append(tmp2)
        return results

# 手掌检测 kpu 运行
def hd_kpu_run(kpu_obj,rgb888p_img):
    global current_kmodel_obj
    current_kmodel_obj = kpu_obj
    # (1)原图预处理，并设置模型输入
    hd_kpu_pre_process(rgb888p_img)
    # (2)手掌检测 kpu 运行
    with ScopedTiming("hd_kpu_run",debug_mode > 0):
        current_kmodel_obj.run()
    # (3)释放手掌检测 ai2d 资源
    hd_ai2d_release()
    # (4)获取手掌检测 kpu 输出
    results = hd_kpu_get_output()
    # (5)手掌检测 kpu 结果后处理
    dets = aicube.anchorbasedet_post_process( results[0], results[1], results[2], hd_kmodel_frame_size, hd_frame_size, strides, num_classes, confidence_threshold, nms_threshold, anchors, nms_option)  # kpu结果后处理
    # (6)返回手掌检测结果
    return dets

# 手掌检测 kpu 释放内存
def hd_kpu_deinit():
    with ScopedTiming("hd_kpu_deinit",debug_mode > 0):
        if 'hd_ai2d' in globals():                             #删除hd_ai2d变量，释放对它所引用对象的内存引用
            global hd_ai2d
            del hd_ai2d
        if 'hd_ai2d_output_tensor' in globals():               #删除hd_ai2d_output_tensor变量，释放对它所引用对象的内存引用
            global hd_ai2d_output_tensor
            del hd_ai2d_output_tensor
        if 'hd_ai2d_builder' in globals():                     #删除hd_ai2d_builder变量，释放对它所引用对象的内存引用
            global hd_ai2d_builder
            del hd_ai2d_builder


#-------hand keypoint detection------:
# 手掌关键点检测 ai2d 初始化
def hk_ai2d_init():
    with ScopedTiming("hk_ai2d_init",debug_mode > 0):
        global hk_ai2d, hk_ai2d_output_tensor
        hk_ai2d = nn.ai2d()
        hk_ai2d.set_dtype(nn.ai2d_format.NCHW_FMT,
                                       nn.ai2d_format.NCHW_FMT,
                                       np.uint8, np.uint8)
        data = np.ones(hk_kmodel_input_shape, dtype=np.uint8)
        hk_ai2d_output_tensor = nn.from_numpy(data)

# 手掌关键点检测 ai2d 运行
def hk_ai2d_run(rgb888p_img, x, y, w, h):
    with ScopedTiming("hk_ai2d_run",debug_mode > 0):
        global hk_ai2d,hk_ai2d_input_tensor,hk_ai2d_output_tensor
        hk_ai2d_input = rgb888p_img.to_numpy_ref()
        hk_ai2d_input_tensor = nn.from_numpy(hk_ai2d_input)

        hk_ai2d.set_crop_param(True, x, y, w, h)
        hk_ai2d.set_resize_param(True, nn.interp_method.tf_bilinear, nn.interp_mode.half_pixel )

        global hk_ai2d_builder
        hk_ai2d_builder = hk_ai2d.build([1,3,OUT_RGB888P_HEIGHT,OUT_RGB888P_WIDTH], [1,3,hk_kmodel_frame_size[1],hk_kmodel_frame_size[0]])
        hk_ai2d_builder.run(hk_ai2d_input_tensor, hk_ai2d_output_tensor)

# 手掌关键点检测 ai2d 释放内存
def hk_ai2d_release():
    with ScopedTiming("hk_ai2d_release",debug_mode > 0):
        global hk_ai2d_input_tensor, hk_ai2d_builder
        del hk_ai2d_input_tensor
        del hk_ai2d_builder

# 手掌关键点检测 kpu 初始化
def hk_kpu_init(hk_kmodel_file):
    # init kpu and load kmodel
    with ScopedTiming("hk_kpu_init",debug_mode > 0):
        hk_kpu_obj = nn.kpu()
        hk_kpu_obj.load_kmodel(hk_kmodel_file)

        hk_ai2d_init()
        return hk_kpu_obj

# 手掌关键点检测 kpu 输入预处理
def hk_kpu_pre_process(rgb888p_img, x, y, w, h):
    hk_ai2d_run(rgb888p_img, x, y, w, h)
    with ScopedTiming("hk_kpu_pre_process",debug_mode > 0):
        global current_kmodel_obj,hk_ai2d_output_tensor
        # set kpu input
        current_kmodel_obj.set_input_tensor(0, hk_ai2d_output_tensor)

# 手掌关键点检测 kpu 获得 kmodel 输出
def hk_kpu_get_output():
    with ScopedTiming("hk_kpu_get_output",debug_mode > 0):
        global current_kmodel_obj
        results = []
        for i in range(current_kmodel_obj.outputs_size()):
            data = current_kmodel_obj.get_output_tensor(i)
            result = data.to_numpy()

            result = result.reshape((result.shape[0]*result.shape[1]))
            tmp2 = result.copy()
            del result
            results.append(tmp2)
        return results

# 手掌关键点检测 kpu 输出后处理
def hk_kpu_post_process(results, x, y, w, h):
    results_show = np.zeros(results.shape,dtype=np.int16)
    results_show[0::2] = results[0::2] * w + x
    results_show[1::2] = results[1::2] * h + y
    return results_show

# 手掌关键点检测 kpu 运行
def hk_kpu_run(kpu_obj,rgb888p_img, x, y, w, h):
    global current_kmodel_obj
    current_kmodel_obj = kpu_obj
    # (1)原图预处理，并设置模型输入
    hk_kpu_pre_process(rgb888p_img, x, y, w, h)
    # (2)手掌关键点检测 kpu 运行
    with ScopedTiming("hk_kpu_run",debug_mode > 0):
        current_kmodel_obj.run()
    # (3)释放手掌关键点检测 ai2d 资源
    hk_ai2d_release()
    # (4)获取手掌关键点检测 kpu 输出
    results = hk_kpu_get_output()
    # (5)手掌关键点检测 kpu 结果后处理
    result = hk_kpu_post_process(results[0],x,y,w,h)
    # (6)返回手掌关键点检测结果
    return result

# 手掌关键点检测 kpu 释放内存
def hk_kpu_deinit():
    with ScopedTiming("hk_kpu_deinit",debug_mode > 0):
        if 'hk_ai2d' in globals():                             #删除hk_ai2d变量，释放对它所引用对象的内存引用
            global hk_ai2d
            del hk_ai2d
        if 'hk_ai2d_output_tensor' in globals():               #删除hk_ai2d_output_tensor变量，释放对它所引用对象的内存引用
            global hk_ai2d_output_tensor
            del hk_ai2d_output_tensor

# 求两个vector之间的夹角
def hk_vector_2d_angle(v1,v2):
    with ScopedTiming("hk_vector_2d_angle",debug_mode > 0):
        v1_x = v1[0]
        v1_y = v1[1]
        v2_x = v2[0]
        v2_y = v2[1]
        v1_norm = np.sqrt(v1_x * v1_x+ v1_y * v1_y)
        v2_norm = np.sqrt(v2_x * v2_x + v2_y * v2_y)
        dot_product = v1_x * v2_x + v1_y * v2_y
        cos_angle = dot_product/(v1_norm*v2_norm)
        angle = np.acos(cos_angle)*180/np.pi
        return angle

# 根据手掌关键点检测结果判断手势类别
def hk_gesture(results):
    with ScopedTiming("hk_gesture",debug_mode > 0):
        angle_list = []
        for i in range(5):
            angle = hk_vector_2d_angle([(results[0]-results[i*8+4]), (results[1]-results[i*8+5])],[(results[i*8+6]-results[i*8+8]),(results[i*8+7]-results[i*8+9])])
            angle_list.append(angle)

        thr_angle = 65.
        thr_angle_thumb = 53.
        thr_angle_s = 49.
        gesture_str = None
        if 65535. not in angle_list:
            if (angle_list[0]>thr_angle_thumb)  and (angle_list[1]>thr_angle) and (angle_list[2]>thr_angle) and (angle_list[3]>thr_angle) and (angle_list[4]>thr_angle):
                gesture_str = "fist"
            elif (angle_list[0]<thr_angle_s)  and (angle_list[1]<thr_angle_s) and (angle_list[2]<thr_angle_s) and (angle_list[3]<thr_angle_s) and (angle_list[4]<thr_angle_s):
                gesture_str = "five"
            elif (angle_list[0]<thr_angle_s)  and (angle_list[1]<thr_angle_s) and (angle_list[2]>thr_angle) and (angle_list[3]>thr_angle) and (angle_list[4]>thr_angle):
                gesture_str = "gun"
            elif (angle_list[0]<thr_angle_s)  and (angle_list[1]<thr_angle_s) and (angle_list[2]>thr_angle) and (angle_list[3]>thr_angle) and (angle_list[4]<thr_angle_s):
                gesture_str = "love"
            elif (angle_list[0]>5)  and (angle_list[1]<thr_angle_s) and (angle_list[2]>thr_angle) and (angle_list[3]>thr_angle) and (angle_list[4]>thr_angle):
                gesture_str = "one"
            elif (angle_list[0]<thr_angle_s)  and (angle_list[1]>thr_angle) and (angle_list[2]>thr_angle) and (angle_list[3]>thr_angle) and (angle_list[4]<thr_angle_s):
                gesture_str = "six"
            elif (angle_list[0]>thr_angle_thumb)  and (angle_list[1]<thr_angle_s) and (angle_list[2]<thr_angle_s) and (angle_list[3]<thr_angle_s) and (angle_list[4]>thr_angle):
                gesture_str = "three"
            elif (angle_list[0]<thr_angle_s)  and (angle_list[1]>thr_angle) and (angle_list[2]>thr_angle) and (angle_list[3]>thr_angle) and (angle_list[4]>thr_angle):
                gesture_str = "thumbUp"
            elif (angle_list[0]>thr_angle_thumb)  and (angle_list[1]<thr_angle_s) and (angle_list[2]<thr_angle_s) and (angle_list[3]>thr_angle) and (angle_list[4]>thr_angle):
                gesture_str = "yeah"

        return gesture_str

#-------dynamic gesture--------:
# 动态手势识别 ai2d 初始化
def gesture_ai2d_init(kpu_obj, resize_shape):
    with ScopedTiming("gesture_ai2d_init",debug_mode > 0):
        global gesture_ai2d_resize, gesture_ai2d_resize_builder
        global gesture_ai2d_crop, gesture_ai2d_crop_builder
        global gesture_ai2d_middle_output_tensor, gesture_ai2d_output_tensor

        ori_w = OUT_RGB888P_WIDTH
        ori_h = OUT_RGB888P_HEIGHT
        width = gesture_kmodel_frame_size[0]
        height = gesture_kmodel_frame_size[1]
        ratiow = float(resize_shape) / ori_w
        ratioh = float(resize_shape) / ori_h
        if ratiow < ratioh:
            ratio = ratioh
        else:
            ratio = ratiow
        new_w = int(ratio * ori_w)
        new_h = int(ratio * ori_h)

        top = int((new_h-height)/2)
        left = int((new_w-width)/2)

        gesture_ai2d_resize = nn.ai2d()
        gesture_ai2d_resize.set_dtype(nn.ai2d_format.NCHW_FMT, nn.ai2d_format.NCHW_FMT, np.uint8, np.uint8)
        gesture_ai2d_resize.set_resize_param(True, nn.interp_method.tf_bilinear, nn.interp_mode.half_pixel)
        gesture_ai2d_resize_builder = gesture_ai2d_resize.build([1,3,OUT_RGB888P_HEIGHT,OUT_RGB888P_WIDTH], [1,3,new_h,new_w])

        gesture_ai2d_crop = nn.ai2d()
        gesture_ai2d_crop.set_dtype(nn.ai2d_format.NCHW_FMT, nn.ai2d_format.NCHW_FMT, np.uint8, np.uint8)
        gesture_ai2d_crop.set_crop_param(True, left, top, width, height)
        gesture_ai2d_crop_builder = gesture_ai2d_crop.build([1,3,new_h,new_w], [1,3,height,width])

        global gesture_kpu_input_tensor, gesture_kpu_input_tensors, current_kmodel_obj
        current_kmodel_obj = kpu_obj
        gesture_kpu_input_tensors = []
        for i in range(current_kmodel_obj.inputs_size()):
            data = np.zeros(gesture_kmodel_input_shape[i], dtype=np.float)
            gesture_kpu_input_tensor = nn.from_numpy(data)
            gesture_kpu_input_tensors.append(gesture_kpu_input_tensor)

        data = np.ones(gesture_kmodel_input_shape[0], dtype=np.uint8)
        gesture_ai2d_output_tensor = nn.from_numpy(data)

        global data_float
        data_float = np.ones(gesture_kmodel_input_shape[0], dtype=np.float)

        data_middle = np.ones((1,3,new_h,new_w), dtype=np.uint8)
        gesture_ai2d_middle_output_tensor = nn.from_numpy(data_middle)

def gesture_ai2d_run(rgb888p_img):
    with ScopedTiming("gesture_ai2d_run",debug_mode > 0):
        global gesture_ai2d_input_tensor, gesture_kpu_input_tensors, gesture_ai2d_middle_output_tensor, gesture_ai2d_output_tensor
        global gesture_ai2d_resize_builder, gesture_ai2d_crop_builder

        gesture_ai2d_input = rgb888p_img.to_numpy_ref()
        gesture_ai2d_input_tensor = nn.from_numpy(gesture_ai2d_input)

        gesture_ai2d_resize_builder.run(gesture_ai2d_input_tensor, gesture_ai2d_middle_output_tensor)
        gesture_ai2d_crop_builder.run(gesture_ai2d_middle_output_tensor, gesture_ai2d_output_tensor)

        result = gesture_ai2d_output_tensor.to_numpy()
        global data_float
        data_float[0] = result[0].copy()
        data_float[0] = (data_float[0]*1.0/255 -mean_values)/std_values
        tmp = nn.from_numpy(data_float)
        gesture_kpu_input_tensors[0] = tmp

# 动态手势识别 ai2d 释放内存
def gesture_ai2d_release():
    with ScopedTiming("gesture_ai2d_release",debug_mode > 0):
        global gesture_ai2d_input_tensor
        del gesture_ai2d_input_tensor

# 动态手势识别 kpu 初始化
def gesture_kpu_init(gesture_kmodel_file):
    # init kpu and load kmodel
    with ScopedTiming("gesture_kpu_init",debug_mode > 0):
        gesture_kpu_obj = nn.kpu()
        gesture_kpu_obj.load_kmodel(gesture_kmodel_file)
        gesture_ai2d_init(gesture_kpu_obj, resize_shape)
        return gesture_kpu_obj

# 动态手势识别 kpu 输入预处理
def gesture_kpu_pre_process(rgb888p_img):
    gesture_ai2d_run(rgb888p_img)
    with ScopedTiming("gesture_kpu_pre_process",debug_mode > 0):
        global current_kmodel_obj,gesture_kpu_input_tensors
        # set kpu input
        for i in range(current_kmodel_obj.inputs_size()):
            current_kmodel_obj.set_input_tensor(i, gesture_kpu_input_tensors[i])

# 动态手势识别 kpu 获得 kmodel 输出
def gesture_kpu_get_output():
    with ScopedTiming("gesture_kpu_get_output",debug_mode > 0):
        global current_kmodel_obj, gesture_kpu_input_tensors
        for i in range(current_kmodel_obj.outputs_size()):
            data = current_kmodel_obj.get_output_tensor(i)
            if (i==0):
                result = data.to_numpy()
                tmp2 = result.copy()
            else:
                gesture_kpu_input_tensors[i] = data
        return tmp2

# 动态手势识别结果处理
def gesture_process_output(pred,history):
    if (pred == 7 or pred == 8 or pred == 21 or pred == 22 or pred == 3 ):
        pred = history[-1]
    if (pred == 0 or pred == 4 or pred == 6 or pred == 9 or pred == 14 or pred == 1 or pred == 19 or pred == 20 or pred == 23 or pred == 24) :
        pred = history[-1]
    if (pred == 0) :
        pred = 2
    if (pred != history[-1]) :
        if (len(history)>= 2) :
            if (history[-1] != history[len(history)-2]) :
                pred = history[-1]
    history.append(pred)
    if (len(history) > max_hist_len) :
        history = history[-max_hist_len:]
    return history[-1]

# 动态手势识别结果后处理
def gesture_kpu_post_process(results, his_logit, history):
    with ScopedTiming("gesture_kpu_post_process",debug_mode > 0):
        his_logit.append(results[0])
        avg_logit = sum(np.array(his_logit))
        idx_ = np.argmax(avg_logit)

        idx = gesture_process_output(idx_, history)
        if (idx_ != idx):
            his_logit_last = his_logit[-1]
            his_logit = []
            his_logit.append(his_logit_last)
        return idx, avg_logit

# 动态手势识别 kpu 运行
def gesture_kpu_run(kpu_obj,rgb888p_img, his_logit, history):
    global current_kmodel_obj
    current_kmodel_obj = kpu_obj
    # (1)原图预处理，并设置模型输入
    gesture_kpu_pre_process(rgb888p_img)
    # (2)动态手势识别 kpu 运行
    with ScopedTiming("gesture_kpu_run",debug_mode > 0):
        current_kmodel_obj.run()
    # (3)释放动态手势识别 ai2d 资源
    gesture_ai2d_release()
    # (4)获取动态手势识别 kpu 输出
    results = gesture_kpu_get_output()
    # (5)动态手势识别 kpu 结果后处理
    result,  avg_logit= gesture_kpu_post_process(results,his_logit, history)
    # (6)返回动态手势识别结果
    return result, avg_logit

def gesture_kpu_deinit():
    with ScopedTiming("gesture_kpu_deinit",debug_mode > 0):
        if 'gesture_ai2d_resize' in globals():                             #删除gesture_ai2d_resize变量，释放对它所引用对象的内存引用
            global gesture_ai2d_resize
            del gesture_ai2d_resize
        if 'gesture_ai2d_middle_output_tensor' in globals():               #删除gesture_ai2d_middle_output_tensor变量，释放对它所引用对象的内存引用
            global gesture_ai2d_middle_output_tensor
            del gesture_ai2d_middle_output_tensor
        if 'gesture_ai2d_crop' in globals():                               #删除gesture_ai2d_crop变量，释放对它所引用对象的内存引用
            global gesture_ai2d_crop
            del gesture_ai2d_crop
        if 'gesture_ai2d_output_tensor' in globals():                      #删除gesture_ai2d_output_tensor变量，释放对它所引用对象的内存引用
            global gesture_ai2d_output_tensor
            del gesture_ai2d_output_tensor
        if 'gesture_kpu_input_tensors' in globals():                       #删除gesture_kpu_input_tensors变量，释放对它所引用对象的内存引用
            global gesture_kpu_input_tensors
            del gesture_kpu_input_tensors
        if 'gesture_ai2d_resize_builder' in globals():                     #删除gesture_ai2d_resize_builder变量，释放对它所引用对象的内存引用
            global gesture_ai2d_resize_builder
            del gesture_ai2d_resize_builder
        if 'gesture_ai2d_crop_builder' in globals():                       #删除gesture_ai2d_crop_builder变量，释放对它所引用对象的内存引用
            global gesture_ai2d_crop_builder
            del gesture_ai2d_crop_builder


#media_utils.py
global draw_img,osd_img,draw_numpy                          #for display 定义全局 作图image对象
global buffer,media_source,media_sink                       #for media   定义 media 程序中的中间存储对象

#for display 初始化
def display_init():
    # use hdmi for display
    display.init(LT9611_1920X1080_30FPS)
    display.set_plane(0, 0, DISPLAY_WIDTH, DISPLAY_HEIGHT, PIXEL_FORMAT_YVU_PLANAR_420, DISPLAY_MIRROR_NONE, DISPLAY_CHN_VIDEO1)

# display 释放内存
def display_deinit():
    display.deinit()

#for camera 初始化
def camera_init(dev_id):
    camera.sensor_init(dev_id, CAM_DEFAULT_SENSOR)

    # set chn0 output yuv420sp
    camera.set_outsize(dev_id, CAM_CHN_ID_0, DISPLAY_WIDTH, DISPLAY_HEIGHT)
    camera.set_outfmt(dev_id, CAM_CHN_ID_0, PIXEL_FORMAT_YUV_SEMIPLANAR_420)

    # set chn2 output rgb88planar
    camera.set_outsize(dev_id, CAM_CHN_ID_2, OUT_RGB888P_WIDTH, OUT_RGB888P_HEIGHT)
    camera.set_outfmt(dev_id, CAM_CHN_ID_2, PIXEL_FORMAT_RGB_888_PLANAR)

# camera 开启
def camera_start(dev_id):
    camera.start_stream(dev_id)

# camera 读取图像
def camera_read(dev_id):
    with ScopedTiming("camera_read",debug_mode >0):
        rgb888p_img = camera.capture_image(dev_id, CAM_CHN_ID_2)
        return rgb888p_img

# camera 图像释放
def camera_release_image(dev_id,rgb888p_img):
    with ScopedTiming("camera_release_image",debug_mode >0):
        camera.release_image(dev_id, CAM_CHN_ID_2, rgb888p_img)

# camera 结束
def camera_stop(dev_id):
    camera.stop_stream(dev_id)

#for media 初始化
def media_init():
    config = k_vb_config()
    config.max_pool_cnt = 1
    config.comm_pool[0].blk_size = 4 * DISPLAY_WIDTH * DISPLAY_HEIGHT
    config.comm_pool[0].blk_cnt = 1
    config.comm_pool[0].mode = VB_REMAP_MODE_NOCACHE

    media.buffer_config(config)

    global media_source, media_sink
    media_source = media_device(CAMERA_MOD_ID, CAM_DEV_ID_0, CAM_CHN_ID_0)
    media_sink = media_device(DISPLAY_MOD_ID, DISPLAY_DEV_ID, DISPLAY_CHN_VIDEO1)
    media.create_link(media_source, media_sink)

    # 初始化多媒体buffer
    media.buffer_init()

    global buffer, draw_img, osd_img, draw_numpy
    buffer = media.request_buffer(4 * DISPLAY_WIDTH * DISPLAY_HEIGHT)
    # 图层1，用于画框
    draw_numpy = np.zeros((DISPLAY_HEIGHT, DISPLAY_WIDTH,4), dtype=np.uint8)
    draw_img = image.Image(DISPLAY_WIDTH, DISPLAY_HEIGHT, image.ARGB8888, alloc=image.ALLOC_REF, data=draw_numpy)
    # 图层2，用于拷贝画框结果，防止画框过程中发生buffer搬运
    osd_img = image.Image(DISPLAY_WIDTH, DISPLAY_HEIGHT, image.ARGB8888, poolid=buffer.pool_id, alloc=image.ALLOC_VB,
                          phyaddr=buffer.phys_addr, virtaddr=buffer.virt_addr)

# media 释放内存
def media_deinit():
    os.exitpoint(os.EXITPOINT_ENABLE_SLEEP)
    time.sleep_ms(100)
    if 'buffer' in globals():
        global buffer
        media.release_buffer(buffer)
    if 'media_source' in globals() and 'media_sink' in globals():
        global media_source, media_sink
        media.destroy_link(media_source, media_sink)

    media.buffer_deinit()

#**********for dynamic_gesture.py**********
def dynamic_gesture_inference():
    print("dynamic_gesture_test start")
    cur_state = TRIGGER
    pre_state = TRIGGER
    draw_state = TRIGGER

    kpu_hand_detect = hd_kpu_init(hd_kmodel_file)                       # 创建手掌检测的 kpu 对象
    kpu_hand_keypoint_detect = hk_kpu_init(hk_kmodel_file)              # 创建手掌关键点检测的 kpu 对象
    kpu_dynamic_gesture = gesture_kpu_init(gesture_kmodel_file)         # 创建动态手势识别的 kpu 对象
    camera_init(CAM_DEV_ID_0)                                           # 初始化 camera
    display_init()                                                      # 初始化 display

    try:
        media_init()

        camera_start(CAM_DEV_ID_0)
        vec_flag = []
        his_logit = []
        history = [2]
        s_start = time.time_ns()

        count = 0
        global draw_img,draw_numpy,osd_img
        while True:
            # 设置当前while循环退出点，保证rgb888p_img正确释放
            os.exitpoint()
            with ScopedTiming("total",1):
                rgb888p_img = camera_read(CAM_DEV_ID_0)                 # 读取一帧图片

                # for rgb888planar
                if rgb888p_img.format() == image.RGBP888:
                    draw_img.clear()
                    if (cur_state == TRIGGER):
                        with ScopedTiming("trigger time", debug_mode > 0):
                            dets = hd_kpu_run(kpu_hand_detect,rgb888p_img)                                                  # 执行手掌检测 kpu 运行 以及 后处理过程

                            for det_box in dets:
                                x1, y1, x2, y2 = int(det_box[2]),int(det_box[3]),int(det_box[4]),int(det_box[5])
                                w = int(x2 - x1)
                                h = int(y2 - y1)

                                if (h<(0.1*OUT_RGB888P_HEIGHT)):
                                    continue
                                if (w<(0.25*OUT_RGB888P_WIDTH) and ((x1<(0.03*OUT_RGB888P_WIDTH)) or (x2>(0.97*OUT_RGB888P_WIDTH)))):
                                    continue
                                if (w<(0.15*OUT_RGB888P_WIDTH) and ((x1<(0.01*OUT_RGB888P_WIDTH)) or (x2>(0.99*OUT_RGB888P_WIDTH)))):
                                    continue

                                length = max(w,h)/2
                                cx = (x1+x2)/2
                                cy = (y1+y2)/2
                                ratio_num = 1.26*length

                                x1_kp = int(max(0,cx-ratio_num))
                                y1_kp = int(max(0,cy-ratio_num))
                                x2_kp = int(min(OUT_RGB888P_WIDTH-1, cx+ratio_num))
                                y2_kp = int(min(OUT_RGB888P_HEIGHT-1, cy+ratio_num))
                                w_kp = int(x2_kp - x1_kp + 1)
                                h_kp = int(y2_kp - y1_kp + 1)

                                hk_results = hk_kpu_run(kpu_hand_keypoint_detect,rgb888p_img, x1_kp, y1_kp, w_kp, h_kp)     # 执行手掌关键点检测 kpu 运行 以及 后处理过程
                                gesture = hk_gesture(hk_results)                                                            # 根据关键点检测结果判断手势类别

                                if ((gesture == "five") or (gesture == "yeah")):
                                    v_x = hk_results[24]-hk_results[0]
                                    v_y = hk_results[25]-hk_results[1]
                                    angle = hk_vector_2d_angle([v_x,v_y],[1.0,0.0])                                         # 计算手指（中指）的朝向

                                    if (v_y>0):
                                        angle = 360-angle

                                    if ((70.0<=angle) and (angle<110.0)):                                                   # 手指向上
                                        if ((pre_state != UP) or (pre_state != MIDDLE)):
                                            vec_flag.append(pre_state)
                                        if ((len(vec_flag)>10)or(pre_state == UP) or (pre_state == MIDDLE) or(pre_state == TRIGGER)):
                                            draw_numpy[:bin_height,:bin_width,:] = shang_argb
                                            cur_state = UP

                                    elif ((110.0<=angle) and (angle<225.0)):                                                # 手指向右(实际方向)
                                        if (pre_state != RIGHT):
                                            vec_flag.append(pre_state)
                                        if ((len(vec_flag)>10)or(pre_state == RIGHT)or(pre_state == TRIGGER)):
                                            draw_numpy[:bin_width,:bin_height,:] = you_argb
                                            cur_state = RIGHT

                                    elif((225.0<=angle) and (angle<315.0)):                                                 # 手指向下
                                        if (pre_state != DOWN):
                                            vec_flag.append(pre_state)
                                        if ((len(vec_flag)>10)or(pre_state == DOWN)or(pre_state == TRIGGER)):
                                            draw_numpy[:bin_height,:bin_width,:] = xia_argb
                                            cur_state = DOWN

                                    else:                                                                                   # 手指向左(实际方向)
                                        if (pre_state != LEFT):
                                            vec_flag.append(pre_state)
                                        if ((len(vec_flag)>10)or(pre_state == LEFT)or(pre_state == TRIGGER)):
                                            draw_numpy[:bin_width,:bin_height,:] = zuo_argb
                                            cur_state = LEFT

                                    m_start = time.time_ns()
                            his_logit = []
                    else:
                        with ScopedTiming("swip time",debug_mode > 0):
                            idx, avg_logit = gesture_kpu_run(kpu_dynamic_gesture,rgb888p_img, his_logit, history)           # 执行动态手势识别 kpu 运行 以及 后处理过程
                            if (cur_state == UP):
                                draw_numpy[:bin_height,:bin_width,:] = shang_argb
                                if ((idx==15) or (idx==10)):
                                    vec_flag.clear()
                                    if (((avg_logit[idx] >= 0.7) and (len(his_logit) >= 2)) or ((avg_logit[idx] >= 0.3) and (len(his_logit) >= 4))):
                                        s_start = time.time_ns()
                                        cur_state = TRIGGER
                                        draw_state = DOWN
                                        history = [2]
                                    pre_state = UP
                                elif ((idx==25)or(idx==26)) :
                                    vec_flag.clear()
                                    if (((avg_logit[idx] >= 0.4) and (len(his_logit) >= 2)) or ((avg_logit[idx] >= 0.3) and (len(his_logit) >= 3))):
                                        s_start = time.time_ns()
                                        cur_state = TRIGGER
                                        draw_state = MIDDLE
                                        history = [2]
                                    pre_state = MIDDLE
                                else:
                                    his_logit.clear()
                            elif (cur_state == RIGHT):
                                draw_numpy[:bin_width,:bin_height,:] = you_argb
                                if  ((idx==16)or(idx==11)) :
                                    vec_flag.clear()
                                    if (((avg_logit[idx] >= 0.4) and (len(his_logit) >= 2)) or ((avg_logit[idx] >= 0.3) and (len(his_logit) >= 3))):
                                        s_start = time.time_ns()
                                        cur_state = TRIGGER
                                        draw_state = RIGHT
                                        history = [2]
                                    pre_state = RIGHT
                                else:
                                    his_logit.clear()
                            elif (cur_state == DOWN):
                                draw_numpy[:bin_height,:bin_width,:] = xia_argb
                                if  ((idx==18)or(idx==13)):
                                    vec_flag.clear()
                                    if (((avg_logit[idx] >= 0.4) and (len(his_logit) >= 2)) or ((avg_logit[idx] >= 0.3) and (len(his_logit) >= 3))):
                                        s_start = time.time_ns()
                                        cur_state = TRIGGER
                                        draw_state = UP
                                        history = [2]
                                    pre_state = DOWN
                                else:
                                    his_logit.clear()
                            elif (cur_state == LEFT):
                                draw_numpy[:bin_width,:bin_height,:] = zuo_argb
                                if ((idx==17)or(idx==12)):
                                    vec_flag.clear()
                                    if (((avg_logit[idx] >= 0.4) and (len(his_logit) >= 2)) or ((avg_logit[idx] >= 0.3) and (len(his_logit) >= 3))):
                                        s_start = time.time_ns()
                                        cur_state = TRIGGER
                                        draw_state = LEFT
                                        history = [2]
                                    pre_state = LEFT
                                else:
                                    his_logit.clear()

                        elapsed_time = round((time.time_ns() - m_start)/1000000)

                        if ((cur_state != TRIGGER) and (elapsed_time>2000)):
                            cur_state = TRIGGER
                            pre_state = TRIGGER

                    elapsed_ms_show = round((time.time_ns()-s_start)/1000000)
                    if (elapsed_ms_show<1000):
                        if (draw_state == UP):
                            draw_img.draw_arrow(1068,330,1068,130, (255,170,190,230), thickness=13)                             # 判断为向上挥动时，画一个向上的箭头
                        elif (draw_state == RIGHT):
                            draw_img.draw_arrow(1290,540,1536,540, (255,170,190,230), thickness=13)                             # 判断为向右挥动时，画一个向右的箭头
                        elif (draw_state == DOWN):
                            draw_img.draw_arrow(1068,750,1068,950, (255,170,190,230), thickness=13)                             # 判断为向下挥动时，画一个向下的箭头
                        elif (draw_state == LEFT):
                            draw_img.draw_arrow(846,540,600,540, (255,170,190,230), thickness=13)                               # 判断为向左挥动时，画一个向左的箭头
                        elif (draw_state == MIDDLE):
                            draw_img.draw_circle(1068,540,100, (255,170,190,230), thickness=2, fill=True)                       # 判断为五指捏合手势时，画一个实心圆
                    else:
                        draw_state = TRIGGER

                camera_release_image(CAM_DEV_ID_0,rgb888p_img)         # camera 释放图像
                if (count>5):
                    gc.collect()
                    count = 0
                else:
                    count += 1

            draw_img.copy_to(osd_img)
            display.show_image(osd_img, 0, 0, DISPLAY_CHN_OSD3)
    except KeyboardInterrupt as e:
        print("user stop: ", e)
    except BaseException as e:
        sys.print_exception(e)
    finally:
        camera_stop(CAM_DEV_ID_0)                                       # 停止 camera
        display_deinit()                                                # 释放 display
        hd_kpu_deinit()                                                 # 释放手掌检测 kpu
        hk_kpu_deinit()                                                 # 释放手掌关键点检测 kpu
        gesture_kpu_deinit()                                            # 释放动态手势识别 kpu
        if 'current_kmodel_obj' in globals():
            global current_kmodel_obj
            del current_kmodel_obj
        del kpu_hand_detect
        del kpu_hand_keypoint_detect
        del kpu_dynamic_gesture

        if 'draw_numpy' in globals():
            global draw_numpy
            del draw_numpy

        if 'draw_img' in globals():
            global draw_img
            del draw_img

        gc.collect()
#        nn.shrink_memory_pool()
        media_deinit()                                                  # 释放 整个media

    print("dynamic_gesture_test end")
    return 0

if __name__ == '__main__':
    os.exitpoint(os.EXITPOINT_ENABLE)
    nn.shrink_memory_pool()
    dynamic_gesture_inference()

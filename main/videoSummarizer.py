# Imports
import argparse
import os
import pysrt
import re
import subprocess
import sys
import math

from moviepy.editor import VideoFileClip, TextClip, ImageClip, concatenate_videoclips

from sumy.parsers.plaintext import PlaintextParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.nlp.stemmers import Stemmer
from sumy.utils import get_stop_words

from sumy.summarizers.luhn import LuhnSummarizer
from sumy.summarizers.edmundson import EdmundsonSummarizer
from sumy.summarizers.lsa import LsaSummarizer
from sumy.summarizers.text_rank import TextRankSummarizer
from sumy.summarizers.lex_rank import LexRankSummarizer

SUMMARIZERS = {
    'luhn': LuhnSummarizer,
    'edmundson': EdmundsonSummarizer,
    'lsa': LsaSummarizer,
    'text-rank': TextRankSummarizer,
    'lex-rank': LexRankSummarizer
}

# Function to concatenate the video to obtain the summary
def create_summary(filename, regions):
    subclips = []
    # obtain video
    input_video = VideoFileClip(filename)
    # Scan through video and store the subclips in an array
    last_end = 0
    for (start, end) in regions:
        subclip = input_video.subclip(start, end)
        subclips.append(subclip)
        last_end = end
    # return the concatenated videoclip to the 
    return concatenate_videoclips(subclips)

# Function to find the range of the subtitles in seconds 
def srt_item_to_range(item):
    start_s = item.start.hours*60*60 + item.start.minutes*60 + item.start.seconds + item.start.milliseconds/1000.
    end_s = item.end.hours*60*60 + item.end.minutes*60 + item.end.seconds + item.end.milliseconds/1000.
    return start_s, end_s

# Function to convert srt file to document in such a way that each sentence starts with '(sentence no)'
# It also removes all the unwanted stray elements in the srt file 
def srt_to_doc(srt_file):
    text = ''
    for index, item in enumerate(srt_file):
        print(item.text)
        if item.text.startswith("["): continue
        text += "(%d) " % index
        text += item.text.replace("\n", "").strip("...").replace(".", "").replace("?", "").replace("!", "")
        text += ". "
    return text

def total_duration_of_regions(regions):
    print(list(map(lambda rangeValue : rangeValue[1]-rangeValue[0] , regions)))
    return sum(list(map(lambda rangeValue : rangeValue[1]-rangeValue[0] , regions)))

def summarize(srt_file, summarizer, n_sentences, language):
    # Converting the srt file to a plain text document and passing in to Sumy library(The text summarization library) functions.
    print(srt_to_doc(srt_file))
    parser = PlaintextParser.from_string(srt_to_doc(srt_file), Tokenizer(language))
    stemmer = Stemmer(language)
    summarizer = SUMMARIZERS[summarizer](stemmer)
    summarizer.stop_words = get_stop_words(language)
    ret = []
    # Now the the document passed is summarized and we can access the filtered sentences along with the no of sentence
    for sentence in summarizer(parser.document, n_sentences):
        # Index of the sentence
        index = int(re.findall("\(([0-9]+)\)", str(sentence))[0])
        # Using the index we determine the subtitle to be selected
        item = srt_file[index]
        # add the selected subtitle to the result array
        ret.append(srt_item_to_range(item))
    return ret

def find_summary_regions(srt_filename, summarizer="lsa", duration=30, language="english"):
    srt_file = pysrt.open(srt_filename)
    print(srt_file)
    # Find the average amount of time required for each subititle to be showned 
    avg_subtitle_duration = total_duration_of_regions(list(map(srt_item_to_range, srt_file)))/len(srt_file)
    # Find the no of sentences that will be required in the summary video
    n_sentences = duration / avg_subtitle_duration
    print(n_sentences)
    # get the summarize video's subtitle array
    summary = summarize(srt_file, summarizer, n_sentences, language)
    # Check whether the total duration is less than the duration required for the video
    total_time = total_duration_of_regions(summary)
    try_higher = total_time < duration
    # If the duration which we got is higher than required 
    if try_higher:
        # Then until the resultant duration is higher than the required duration run a loop in which the no of sentence is increased by 1 
        while total_time < duration:
            n_sentences += 1
            summary = summarize(srt_file, summarizer, n_sentences, language)
            total_time = total_duration_of_regions(summary)
    else:
        # Else if  the duration which we got is lesser than required 
        # Then until the resultant duration is lesser than the required duration run a loop in which the no of sentence is increased by 1 
        while total_time > duration:
            n_sentences -= 1
            summary = summarize(srt_file, summarizer, n_sentences, language)
            total_time = total_duration_of_regions(summary)
    # return the resulant summarized subtitle array 
    return summary


def summarizeVideo(videoName,subtitleName):
    # print("Enter the video filename")
    video=videoName
    # print("Enter the subtitle name ")
    subtitle=subtitleName

    # print("Enter summarizer name ")
    summarizerName='lsa'
    duration=30
    language='english'
    regions = find_summary_regions(subtitle,
                                   summarizer=summarizerName,
                                   duration=duration,
                                   language=language)
    summary = create_summary(video,regions)
    # Converting to video 
    base, ext = os.path.splitext(video)
    dst = "{0}_summarized.mp4".format(base)
    summary.to_videofile(
        dst, 
        codec="libx264", 
        temp_audiofile="temp.m4a",
        remove_temp=True,
        audio_codec="aac",
    )
    return dst
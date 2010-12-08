# Copyright (c) 2009 John Glover, National University of Ireland, Maynooth
# 
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of 
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

import simpl
from simpl import simplsms
import pysms
import numpy as np
from scipy.io.wavfile import read
from nose.tools import assert_almost_equals

class TestSimplSMS(object):
    FLOAT_PRECISION = 3 # number of decimal places to check for accuracy
    input_file = 'audio/flute.wav'
    frame_size = 2048
    hop_size = 512
    num_frames = 9 
    num_samples = frame_size + ((num_frames - 1) * hop_size)
    max_peaks = 10
    max_partials = 10

    def get_audio(self):
        audio_data = read(self.input_file)
        audio = simpl.asarray(audio_data[1]) / 32768.0
        sampling_rate = audio_data[0]
        return audio[0:self.num_samples], sampling_rate

    def pysms_analysis_params(self, sampling_rate):
        analysis_params = pysms.SMS_AnalParams()
        pysms.sms_initAnalParams(analysis_params)
        analysis_params.iSamplingRate = sampling_rate
        analysis_params.iFrameRate = sampling_rate / self.hop_size
        analysis_params.iWindowType = pysms.SMS_WIN_HAMMING
        analysis_params.fDefaultFundamental = 100
        analysis_params.fHighestFreq = 20000
        analysis_params.iFormat = pysms.SMS_FORMAT_HP
        analysis_params.nTracks = self.max_peaks
        analysis_params.peakParams.iMaxPeaks = self.max_peaks
        analysis_params.nGuides = self.max_peaks
        analysis_params.iMaxDelayFrames = 4
        analysis_params.analDelay = 0
        analysis_params.minGoodFrames = 1
        analysis_params.iCleanTracks = 0
        analysis_params.iStochasticType = pysms.SMS_STOC_NONE
        return analysis_params

    def simplsms_analysis_params(self, sampling_rate):
        analysis_params = simplsms.SMS_AnalParams()
        simplsms.sms_initAnalParams(analysis_params)
        analysis_params.iSamplingRate = sampling_rate
        analysis_params.iFrameRate = sampling_rate / self.hop_size
        analysis_params.iWindowType = simplsms.SMS_WIN_HAMMING
        analysis_params.fDefaultFundamental = 100
        analysis_params.fHighestFreq = 20000
        analysis_params.iFormat = simplsms.SMS_FORMAT_HP
        analysis_params.nTracks = self.max_peaks
        analysis_params.maxPeaks = self.max_peaks
        analysis_params.nGuides = self.max_peaks
        analysis_params.iMaxDelayFrames = 4
        analysis_params.analDelay = 0
        analysis_params.minGoodFrames = 1
        analysis_params.iCleanTracks = 0
        analysis_params.iStochasticType = simplsms.SMS_STOC_NONE
        return analysis_params

    def pysms_synthesis_params(self, sampling_rate):
        synth_params = pysms.SMS_SynthParams() 
        pysms.sms_initSynthParams(synth_params)
        synth_params.iSamplingRate = sampling_rate
        synth_params.iSynthesisType = pysms.SMS_STYPE_DET
        synth_params.sizeHop = self.hop_size 
        return synth_params

    def test_size_next_read(self):
        """test_size_next_read
        Make sure pysms PeakDetection is calculating 
        the correct value for the size of the next frame."""
        audio, sampling_rate = self.get_audio()

        pysms.sms_init()
        snd_header = pysms.SMS_SndHeader()
        # Try to open the input file to fill snd_header
        if(pysms.sms_openSF(self.input_file, snd_header)):
            raise NameError("error opening sound file: " + pysms.sms_errorString())
        analysis_params = self.pysms_analysis_params(sampling_rate)
        analysis_params.iMaxDelayFrames = self.num_frames + 1
        if pysms.sms_initAnalysis(analysis_params, snd_header) != 0:
            raise Exception("Error allocating memory for analysis_params")
        analysis_params.nFrames = self.num_frames
        sms_header = pysms.SMS_Header()
        pysms.sms_fillHeader(sms_header, analysis_params, "pysms")

        sample_offset = 0
        pysms_size_new_data = 0
        current_frame = 0
        sms_next_read_sizes = []

        while current_frame < self.num_frames:
            sms_next_read_sizes.append(analysis_params.sizeNextRead)
            sample_offset += pysms_size_new_data
            if((sample_offset + analysis_params.sizeNextRead) < self.num_samples):
                pysms_size_new_data = analysis_params.sizeNextRead
            else:
                pysms_size_new_data = self.num_samples - sample_offset
            # convert frame to floats for libsms
            frame = audio[sample_offset:sample_offset + pysms_size_new_data]
            frame = np.array(frame, dtype=np.float32)
            analysis_data = pysms.SMS_Data()
            pysms.sms_allocFrameH(sms_header, analysis_data)
            status = pysms.sms_analyze(frame, analysis_data, analysis_params)  
            # as the no. of frames of delay is > num_frames, sms_analyze should
            # never get around to performing partial tracking, and so the return
            # value should be 0
            assert status == 0
            pysms.sms_freeFrame(analysis_data)
            current_frame += 1

        pysms.sms_freeAnalysis(analysis_params)
        pysms.sms_closeSF()
        pysms.sms_free()

        pd = simpl.SMSPeakDetection()
        pd.hop_size = self.hop_size
        pd.max_peaks = self.max_peaks
        current_frame = 0
        sample_offset = 0

        while current_frame < self.num_frames:
            pd.frame_size = pd.get_next_frame_size()
            assert sms_next_read_sizes[current_frame] == pd.frame_size
            pd.find_peaks_in_frame(audio[sample_offset:sample_offset + pd.frame_size])
            sample_offset += pd.frame_size
            current_frame += 1

    def test_sms_analyze(self):
        """test_sms_analyze
        Make sure that the simplsms.sms_analyze function does the same thing
        as the sms_analyze function from libsms."""
        audio, sampling_rate = self.get_audio()

        pysms.sms_init()
        snd_header = pysms.SMS_SndHeader()
        # Try to open the input file to fill snd_header
        if(pysms.sms_openSF(self.input_file, snd_header)):
            raise NameError("error opening sound file: " + pysms.sms_errorString())
        analysis_params = self.pysms_analysis_params(sampling_rate)
        analysis_params.iMaxDelayFrames = self.num_frames + 1
        analysis_params.analDelay = 0
        analysis_params.minGoodFrames = 1
        if pysms.sms_initAnalysis(analysis_params, snd_header) != 0:
            raise Exception("Error allocating memory for analysis_params")
        analysis_params.nFrames = self.num_frames
        analysis_params.iSizeSound = self.num_samples
        analysis_params.peakParams.iMaxPeaks = self.max_peaks
        sms_header = pysms.SMS_Header()
        pysms.sms_fillHeader(sms_header, analysis_params, "pysms")

        sample_offset = 0
        size_new_data = 0
        current_frame = 0
        sms_partials = []
        live_partials = [None for i in range(self.max_peaks)]
        do_analysis = True

        while do_analysis and (current_frame < self.num_frames):
            sample_offset += size_new_data
            size_new_data = analysis_params.sizeNextRead
            # convert frame to floats for libsms
            frame = audio[sample_offset:sample_offset + size_new_data]
            frame = np.array(frame, dtype=np.float32)
            analysis_data = pysms.SMS_Data()
            pysms.sms_allocFrameH(sms_header, analysis_data)
            status = pysms.sms_analyze(frame, analysis_data, analysis_params)  

            if status == 1:
                num_partials = analysis_data.nTracks
                sms_freqs = np.zeros(num_partials, dtype=np.float32)
                sms_amps = np.zeros(num_partials, dtype=np.float32)
                sms_phases = np.zeros(num_partials, dtype=np.float32)
                analysis_data.getSinFreq(sms_freqs)
                analysis_data.getSinAmp(sms_amps)
                analysis_data.getSinPhase(sms_phases)
                # make partial objects
                for i in range(num_partials):
                    # for each partial, if the mag is > 0, this partial is alive
                    if sms_amps[i] > 0:
                        # create a peak object
                        p = simpl.Peak()
                        p.amplitude = sms_amps[i]
                        p.frequency = sms_freqs[i]
                        p.phase = sms_phases[i]
                        # add this peak to the appropriate partial
                        if not live_partials[i]:
                            live_partials[i] = simpl.Partial()
                            live_partials[i].starting_frame = current_frame
                            sms_partials.append(live_partials[i])
                        live_partials[i].add_peak(p)
                    # if the mag is 0 and this partial was alive, kill it
                else:
                    if live_partials[i]:
                        live_partials[i] = None
            elif status == -1:
                do_analysis = False
            pysms.sms_freeFrame(analysis_data)
            current_frame += 1

        pysms.sms_freeAnalysis(analysis_params)
        pysms.sms_closeSF()
        pysms.sms_free()

        audio, sampling_rate = self.get_audio()
        simplsms.sms_init()
        simpl_analysis_params = self.simplsms_analysis_params(sampling_rate)
        simpl_analysis_params.iMaxDelayFrames = self.num_frames + 1
        if simplsms.sms_initAnalysis(simpl_analysis_params) != 0:
            raise Exception("Error allocating memory for analysis_params")
        simpl_analysis_params.nFrames = self.num_frames
        simpl_analysis_params.iSizeSound = self.num_samples
        simpl_sms_header = simplsms.SMS_Header()
        simplsms.sms_fillHeader(simpl_sms_header, simpl_analysis_params, "simplsms")

        sample_offset = 0
        size_new_data = 0
        current_frame = 0
        simplsms_partials = []
        live_partials = [None for i in range(self.max_peaks)]
        do_analysis = True

        while do_analysis and (current_frame < self.num_frames):
            sample_offset += size_new_data
            size_new_data = simpl_analysis_params.sizeNextRead
            frame = audio[sample_offset:sample_offset + size_new_data]
            analysis_data = simplsms.SMS_Data()
            simplsms.sms_allocFrameH(simpl_sms_header, analysis_data)
            status = simplsms.sms_analyze(frame, analysis_data, simpl_analysis_params)  

            if status == 1:
                num_partials = analysis_data.nTracks
                freqs = simpl.zeros(num_partials)
                amps = simpl.zeros(num_partials)
                phases = simpl.zeros(num_partials)
                analysis_data.getSinFreq(freqs)
                analysis_data.getSinAmp(amps)
                analysis_data.getSinPhase(phases)
                # make partial objects
                for i in range(num_partials):
                    # for each partial, if the mag is > 0, this partial is alive
                    if amps[i] > 0:
                        # create a peak object
                        p = simpl.Peak()
                        p.amplitude = amps[i]
                        p.frequency = freqs[i]
                        p.phase = phases[i]
                        # add this peak to the appropriate partial
                        if not live_partials[i]:
                            live_partials[i] = simpl.Partial()
                            live_partials[i].starting_frame = current_frame
                            simplsms_partials.append(live_partials[i])
                        live_partials[i].add_peak(p)
                    # if the mag is 0 and this partial was alive, kill it
                else:
                    if live_partials[i]:
                        live_partials[i] = None
            elif status == -1:
                do_analysis = False
            simplsms.sms_freeFrame(analysis_data)
            current_frame += 1

        simplsms.sms_freeAnalysis(simpl_analysis_params)
        simplsms.sms_free()

        # make sure both have the same number of partials
        assert len(sms_partials) == len(simplsms_partials)

        # make sure each partial is the same
        for i in range(len(sms_partials)):
            assert sms_partials[i].get_length() == simplsms_partials[i].get_length()
            for peak_number in range(sms_partials[i].get_length()):
                assert_almost_equals(sms_partials[i].peaks[peak_number].amplitude,
                                     simplsms_partials[i].peaks[peak_number].amplitude,
                                     self.FLOAT_PRECISION)
                assert_almost_equals(sms_partials[i].peaks[peak_number].frequency,
                                     simplsms_partials[i].peaks[peak_number].frequency,
                                     self.FLOAT_PRECISION)
                assert_almost_equals(sms_partials[i].peaks[peak_number].phase,
                                     simplsms_partials[i].peaks[peak_number].phase,
                                     self.FLOAT_PRECISION)

    def test_multi_sms_peak_detection(self): 
        """test_multi_sms_peak_detection
        Test that running the same peak detection process twice in a row
        produces the same results each time. This makes sure that results
        are independent, and also helps to highlight any memory errors."""
        audio, sampling_rate = self.get_audio()
        simplsms.sms_init()
        analysis_params = self.simplsms_analysis_params(sampling_rate)
        analysis_params.iMaxDelayFrames = self.num_frames + 1
        if simplsms.sms_initAnalysis(analysis_params) != 0:
            raise Exception("Error allocating memory for analysis_params")
        analysis_params.nFrames = self.num_frames
        sms_header = simplsms.SMS_Header()
        simplsms.sms_fillHeader(sms_header, analysis_params, "simplsms")

        sample_offset = 0
        size_new_data = 0
        current_frame = 0
        peaks1 = []

        while current_frame < self.num_frames:
            sample_offset += size_new_data
            size_new_data = analysis_params.sizeNextRead
            frame = audio[sample_offset:sample_offset + size_new_data]
            analysis_data = simplsms.SMS_Data()
            simplsms.sms_allocFrameH(sms_header, analysis_data)
            status = simplsms.sms_analyze(frame, analysis_data, analysis_params)  
            # as the no. of frames of delay is > num_frames, sms_analyze should
            # never get around to performing partial tracking, and so the return
            # value should be 0
            assert status == 0
            num_peaks = analysis_data.nTracks
            frame_peaks = []
            simplsms_freqs = simpl.zeros(num_peaks)
            simplsms_amps = simpl.zeros(num_peaks)
            simplsms_phases = simpl.zeros(num_peaks)
            analysis_data.getSinFreq(simplsms_freqs)
            analysis_data.getSinAmp(simplsms_amps)
            analysis_data.getSinPhase(simplsms_phases)
            for i in range(num_peaks):
                if simplsms_amps[i]:
                    p = simpl.Peak()
                    # convert amplitude back to linear
                    p.amplitude = 10**(simplsms_amps[i]/20.0)
                    p.frequency = simplsms_freqs[i]
                    p.phase = simplsms_phases[i]
                    frame_peaks.append(p)
            peaks1.append(frame_peaks)
            pysms.sms_freeFrame(analysis_data)
            current_frame += 1

        simplsms.sms_freeAnalysis(analysis_params)
        simplsms.sms_free()

        # Second run
        audio, sampling_rate = self.get_audio()
        simplsms.sms_init()
        analysis_params = self.simplsms_analysis_params(sampling_rate)
        analysis_params.iMaxDelayFrames = self.num_frames + 1
        if simplsms.sms_initAnalysis(analysis_params) != 0:
            raise Exception("Error allocating memory for analysis_params")
        analysis_params.nFrames = self.num_frames
        sms_header = simplsms.SMS_Header()
        simplsms.sms_fillHeader(sms_header, analysis_params, "simplsms")

        sample_offset = 0
        size_new_data = 0
        current_frame = 0
        peaks2 = []

        while current_frame < self.num_frames:
            sample_offset += size_new_data
            size_new_data = analysis_params.sizeNextRead
            frame = audio[sample_offset:sample_offset + size_new_data]
            analysis_data = simplsms.SMS_Data()
            simplsms.sms_allocFrameH(sms_header, analysis_data)
            status = simplsms.sms_analyze(frame, analysis_data, analysis_params)  
            # as the no. of frames of delay is > num_frames, sms_analyze should
            # never get around to performing partial tracking, and so the return
            # value should be 0
            assert status == 0
            num_peaks = analysis_data.nTracks
            frame_peaks = []
            simplsms_freqs = simpl.zeros(num_peaks)
            simplsms_amps = simpl.zeros(num_peaks)
            simplsms_phases = simpl.zeros(num_peaks)
            analysis_data.getSinFreq(simplsms_freqs)
            analysis_data.getSinAmp(simplsms_amps)
            analysis_data.getSinPhase(simplsms_phases)
            for i in range(num_peaks):
                if simplsms_amps[i]:
                    p = simpl.Peak()
                    # convert amplitude back to linear
                    p.amplitude = 10**(simplsms_amps[i]/20.0)
                    p.frequency = simplsms_freqs[i]
                    p.phase = simplsms_phases[i]
                    frame_peaks.append(p)
            peaks2.append(frame_peaks)
            pysms.sms_freeFrame(analysis_data)
            current_frame += 1

        simplsms.sms_freeAnalysis(analysis_params)
        simplsms.sms_free()

        # make sure we have the same number of frames in each run
        assert len(peaks1) == len(peaks2)
        for f in range(len(peaks1)):
            # in each frame, make sure that we have the same number of peaks
            assert len(peaks1[f]) == len(peaks2[f])
            # make sure that each peak has the same value
            for p in range(len(peaks1[f])):
                assert_almost_equals(peaks1[f][p].frequency, 
                                     peaks2[f][p].frequency,
                                     self.FLOAT_PRECISION)
                assert_almost_equals(peaks1[f][p].amplitude, 
                                     peaks2[f][p].amplitude,
                                     self.FLOAT_PRECISION)
                assert_almost_equals(peaks1[f][p].phase, 
                                     peaks2[f][p].phase,
                                     self.FLOAT_PRECISION)

    def test_multi_simpl_peak_detection(self): 
        """test_multi_simpl_peak_detection
        Test that running the simpl peak detection process twice in a row
        produces the same results each time. This makes sure that results
        are independent, and also helps to highlight any memory errors."""
        audio, sampling_rate = self.get_audio()
        pd = simpl.SMSPeakDetection()
        pd.max_peaks = self.max_peaks
        pd.hop_size = self.hop_size 
        peaks1 = pd.find_peaks(audio)[0:self.num_frames]
        del pd
        # second run
        audio, sampling_rate = self.get_audio()
        pd = simpl.SMSPeakDetection()
        pd.max_peaks = self.max_peaks
        pd.hop_size = self.hop_size 
        peaks2 = pd.find_peaks(audio)[0:self.num_frames]

        # make sure we have the same number of frames in each run
        assert len(peaks1) == len(peaks2)
        for f in range(len(peaks1)):
            # in each frame, make sure that we have the same number of peaks
            assert len(peaks1[f]) == len(peaks2[f])
            # make sure that each peak has the same value
            for p in range(len(peaks1[f])):
                assert_almost_equals(peaks1[f][p].frequency, 
                                     peaks2[f][p].frequency,
                                     self.FLOAT_PRECISION)
                assert_almost_equals(peaks1[f][p].amplitude, 
                                     peaks2[f][p].amplitude,
                                     self.FLOAT_PRECISION)
                assert_almost_equals(peaks1[f][p].phase, 
                                     peaks2[f][p].phase,
                                     self.FLOAT_PRECISION)

    def test_peak_detection(self): 
        """test_peak_detection
        Compare simplsms Peaks with SMS peaks. Exact peak
        information cannot be retrieved using libsms. Basic peak detection
        is performed by sms_detectPeaks, but this is called multiple times
        with different frame sizes by sms_analyze. This peak data cannot
        be returned from sms_analyze without modifying it, so here
        we compare the peaks to a slightly modified version of sms_analyze 
        from simplsms. The peak values should be the same as those found by 
        the simplsms find_peaks function. Analyses have to be performed
        separately due to libsms implementation issues."""
        audio, sampling_rate = self.get_audio()

        simplsms.sms_init()
        analysis_params = self.simplsms_analysis_params(sampling_rate)
        analysis_params.iMaxDelayFrames = self.num_frames + 1
        if simplsms.sms_initAnalysis(analysis_params) != 0:
            raise Exception("Error allocating memory for analysis_params")
        analysis_params.nFrames = self.num_frames
        sms_header = simplsms.SMS_Header()
        simplsms.sms_fillHeader(sms_header, analysis_params, "simplsms")

        sample_offset = 0
        size_new_data = 0
        current_frame = 0
        sms_peaks = []

        while current_frame < self.num_frames:
            sample_offset += size_new_data
            size_new_data = analysis_params.sizeNextRead
            frame = audio[sample_offset:sample_offset + size_new_data]
            analysis_data = simplsms.SMS_Data()
            simplsms.sms_allocFrameH(sms_header, analysis_data)
            status = simplsms.sms_analyze(frame, analysis_data, analysis_params)  
            # as the no. of frames of delay is > num_frames, sms_analyze should
            # never get around to performing partial tracking, and so the return
            # value should be 0
            assert status == 0
            num_peaks = analysis_data.nTracks
            frame_peaks = []
            simplsms_freqs = simpl.zeros(num_peaks)
            simplsms_amps = simpl.zeros(num_peaks)
            simplsms_phases = simpl.zeros(num_peaks)
            analysis_data.getSinFreq(simplsms_freqs)
            analysis_data.getSinAmp(simplsms_amps)
            analysis_data.getSinPhase(simplsms_phases)
            for i in range(num_peaks):
                if simplsms_amps[i]:
                    p = simpl.Peak()
                    # convert amplitude back to linear
                    p.amplitude = 10**(simplsms_amps[i]/20.0)
                    p.frequency = simplsms_freqs[i]
                    p.phase = simplsms_phases[i]
                    frame_peaks.append(p)
            sms_peaks.append(frame_peaks)
            pysms.sms_freeFrame(analysis_data)
            current_frame += 1

        simplsms.sms_freeAnalysis(analysis_params)
        simplsms.sms_free()

        # get simpl peaks
        pd = simpl.SMSPeakDetection()
        pd.hop_size = self.hop_size 
        pd.max_peaks = self.max_peaks
        current_frame = 0
        sample_offset = 0
        simpl_peaks = []

        while current_frame < self.num_frames:
            pd.frame_size = pd.get_next_frame_size()
            simpl_peaks.append(
                    pd.find_peaks_in_frame(audio[sample_offset:sample_offset + pd.frame_size]))
            sample_offset += pd.frame_size
            current_frame += 1

        # make sure we have the same number of frames
        assert len(sms_peaks) == len(simpl_peaks)

        # compare data for each frame
        for frame_number in range(len(sms_peaks)):
            sms_frame = sms_peaks[frame_number]
            simpl_frame = simpl_peaks[frame_number]
            # make sure we have the same number of peaks in each frame
            assert len(sms_frame) == len(simpl_frame)
            # check peak values
            for peak_number in range(len(sms_frame)):
                sms_peak = sms_frame[peak_number]
                simpl_peak = simpl_frame[peak_number]
                assert_almost_equals(sms_peak.amplitude, simpl_peak.amplitude,
                                     self.FLOAT_PRECISION)
                assert_almost_equals(sms_peak.frequency, simpl_peak.frequency,
                                     self.FLOAT_PRECISION)
                assert_almost_equals(sms_peak.phase, simpl_peak.phase,
                                     self.FLOAT_PRECISION)  

    def test_multi_pysms_analyze(self): 
        """test_multi_pysms_analyze
        Test that running the pysms sms_analyze function twice in a row
        produces the same results each time. This makes sure that results
        are independent, and also helps to highlight any memory errors."""
        audio, sampling_rate = self.get_audio()
        pysms.sms_init()
        snd_header = pysms.SMS_SndHeader()
        # Try to open the input file to fill snd_header
        if(pysms.sms_openSF(self.input_file, snd_header)):
            raise NameError("error opening sound file: " + pysms.sms_errorString())
        analysis_params = self.pysms_analysis_params(sampling_rate)
        if pysms.sms_initAnalysis(analysis_params, snd_header) != 0:
            raise Exception("Error allocating memory for analysis_params")
        analysis_params.iSizeSound = self.num_samples
        sms_header = pysms.SMS_Header()
        pysms.sms_fillHeader(sms_header, analysis_params, "pysms")

        sample_offset = 0
        size_new_data = 0
        current_frame = 0
        freqs1 = []
        amps1 = []
        phases1 = []
        do_analysis = True

        while do_analysis and (current_frame < self.num_frames):
            sample_offset += size_new_data
            size_new_data = analysis_params.sizeNextRead
            # convert frame to floats for libsms
            frame = audio[sample_offset:sample_offset + size_new_data]
            frame = np.array(frame, dtype=np.float32)
            analysis_data = pysms.SMS_Data()
            pysms.sms_allocFrameH(sms_header, analysis_data)
            status = pysms.sms_analyze(frame, analysis_data, analysis_params)  
            if status == 1:
                num_partials = analysis_data.nTracks
                freqs = np.zeros(num_partials, dtype=np.float32)
                amps = np.zeros(num_partials, dtype=np.float32)
                phases = np.zeros(num_partials, dtype=np.float32)
                analysis_data.getSinFreq(freqs)
                analysis_data.getSinAmp(amps)
                analysis_data.getSinPhase(phases)
                amps1.append(amps)
                freqs1.append(freqs)
                phases1.append(phases)
            elif status == -1:
                do_analysis = False
            pysms.sms_freeFrame(analysis_data)
            current_frame += 1

        pysms.sms_freeAnalysis(analysis_params)
        pysms.sms_closeSF()
        pysms.sms_free()

        # second run
        audio, sampling_rate = self.get_audio()
        pysms.sms_init()
        snd_header = pysms.SMS_SndHeader()
        # Try to open the input file to fill snd_header
        if(pysms.sms_openSF(self.input_file, snd_header)):
            raise NameError("error opening sound file: " + pysms.sms_errorString())
        analysis_params = self.pysms_analysis_params(sampling_rate)
        if pysms.sms_initAnalysis(analysis_params, snd_header) != 0:
            raise Exception("Error allocating memory for analysis_params")
        analysis_params.iSizeSound = self.num_samples
        sms_header = pysms.SMS_Header()
        pysms.sms_fillHeader(sms_header, analysis_params, "pysms")

        sample_offset = 0
        size_new_data = 0
        current_frame = 0
        freqs2 = []
        amps2 = []
        phases2 = []
        do_analysis = True

        while do_analysis and (current_frame < self.num_frames):
            sample_offset += size_new_data
            size_new_data = analysis_params.sizeNextRead
            # convert frame to floats for libsms
            frame = audio[sample_offset:sample_offset + size_new_data]
            frame = np.array(frame, dtype=np.float32)
            analysis_data = pysms.SMS_Data()
            pysms.sms_allocFrameH(sms_header, analysis_data)
            status = pysms.sms_analyze(frame, analysis_data, analysis_params)  
            if status == 1:
                num_partials = analysis_data.nTracks
                freqs = np.zeros(num_partials, dtype=np.float32)
                amps = np.zeros(num_partials, dtype=np.float32)
                phases = np.zeros(num_partials, dtype=np.float32)
                analysis_data.getSinFreq(freqs)
                analysis_data.getSinAmp(amps)
                analysis_data.getSinPhase(phases)
                amps2.append(amps)
                freqs2.append(freqs)
                phases2.append(phases)
            elif status == -1:
                do_analysis = False
            pysms.sms_freeFrame(analysis_data)
            current_frame += 1

        pysms.sms_freeAnalysis(analysis_params)
        pysms.sms_closeSF()
        pysms.sms_free()

        # make sure we have the same number of results in each run
        assert len(freqs1) == len(freqs2)
        assert len(amps1) == len(amps2)
        assert len(phases1) == len(phases2)

        for r in range(len(freqs1)):
           # in each result, make sure that we have the same number amps, freqs and phases
           assert len(freqs1[r]) == len(freqs2[r])
           assert len(amps1[r]) == len(amps2[r])
           assert len(phases1[r]) == len(phases2[r])
           # make sure that each partial has the same value
           for p in range(len(freqs1[r])):
               assert_almost_equals(freqs1[r][p], freqs2[r][p], self.FLOAT_PRECISION)
               assert_almost_equals(amps1[r][p], amps2[r][p], self.FLOAT_PRECISION)
               assert_almost_equals(phases1[r][p], phases2[r][p], self.FLOAT_PRECISION)

    def test_multi_simpl_partial_tracking(self): 
        """test_multi_simpl_partial_tracking
        Test that running the simpl peak detection process twice in a row
        produces the same results each time. This makes sure that results
        are independent, and also helps to highlight any memory errors."""
        audio, sampling_rate = self.get_audio()
        pd = simpl.SMSPeakDetection()
        pd.max_peaks = self.max_peaks
        pd.hop_size = self.hop_size 
        peaks = pd.find_peaks(audio)[0:self.num_frames]
        pt = simpl.SMSPartialTracking()
        pt.max_partials = self.max_peaks
        partials1 = pt.find_partials(peaks)
        del pd
        del pt
        # second run
        audio, sampling_rate = self.get_audio()
        pd = simpl.SMSPeakDetection()
        pd.max_peaks = self.max_peaks
        pd.hop_size = self.hop_size 
        peaks = pd.find_peaks(audio)[0:self.num_frames]
        pt = simpl.SMSPartialTracking()
        pt.max_partials = self.max_peaks
        partials2 = pt.find_partials(peaks)

        # make sure we have the same number of partials in each run
        print len(partials1), len(partials2)
        assert len(partials1) == len(partials2)
        for p in range(len(partials1)):
            # make sure each partial is the same length
            assert partials1[p].get_length() == partials2[p].get_length()
            # make sure that the peaks in each partial have the same values
            for i in range(partials1[p].get_length()):
                assert_almost_equals(partials1[p].peaks[i].frequency, 
                                     partials2[p].peaks[i].frequency, 
                                     self.FLOAT_PRECISION)
                assert_almost_equals(partials1[p].peaks[i].amplitude, 
                                     partials2[p].peaks[i].amplitude, 
                                     self.FLOAT_PRECISION)
                assert_almost_equals(partials1[p].peaks[i].phase, 
                                     partials2[p].peaks[i].phase, 
                                     self.FLOAT_PRECISION)

    def test_partial_tracking(self):
        """test_partial_tracking
        Compare pysms Partials with SMS partials.""" 
        audio, sampling_rate = self.get_audio()
        pysms.sms_init()
        snd_header = pysms.SMS_SndHeader()
        # Try to open the input file to fill snd_header
        if(pysms.sms_openSF(self.input_file, snd_header)):
            raise NameError("error opening sound file: " + pysms.sms_errorString())
        analysis_params = self.pysms_analysis_params(sampling_rate)
        if pysms.sms_initAnalysis(analysis_params, snd_header) != 0:
            raise Exception("Error allocating memory for analysis_params")
        analysis_params.iSizeSound = self.num_samples
        sms_header = pysms.SMS_Header()
        pysms.sms_fillHeader(sms_header, analysis_params, "pysms")

        sample_offset = 0
        size_new_data = 0
        current_frame = 0
        sms_partials = []
        live_partials = [None for i in range(self.max_peaks)]
        do_analysis = True

        while do_analysis and (current_frame < self.num_frames):
            sample_offset += size_new_data
            size_new_data = analysis_params.sizeNextRead
            # convert frame to floats for libsms
            frame = audio[sample_offset:sample_offset + size_new_data]
            frame = np.array(frame, dtype=np.float32)
            analysis_data = pysms.SMS_Data()
            pysms.sms_allocFrameH(sms_header, analysis_data)
            status = pysms.sms_analyze(frame, analysis_data, analysis_params)  

            if status == 1:
                num_partials = analysis_data.nTracks
                sms_freqs = np.zeros(num_partials, dtype=np.float32)
                sms_amps = np.zeros(num_partials, dtype=np.float32)
                sms_phases = np.zeros(num_partials, dtype=np.float32)
                analysis_data.getSinFreq(sms_freqs)
                analysis_data.getSinAmp(sms_amps)
                analysis_data.getSinPhase(sms_phases)
                # make partial objects
                for i in range(num_partials):
                    # for each partial, if the mag is > 0, this partial is alive
                    if sms_amps[i] > 0:
                        # create a peak object
                        p = simpl.Peak()
                        p.amplitude = sms_amps[i]
                        p.frequency = sms_freqs[i]
                        p.phase = sms_phases[i]
                        # add this peak to the appropriate partial
                        if not live_partials[i]:
                            live_partials[i] = simpl.Partial()
                            live_partials[i].starting_frame = current_frame
                            sms_partials.append(live_partials[i])
                        live_partials[i].add_peak(p)
                    # if the mag is 0 and this partial was alive, kill it
                    else:
                        if live_partials[i]:
                            live_partials[i] = None
            elif status == -1:
                do_analysis = False
            pysms.sms_freeFrame(analysis_data)
            current_frame += 1

        pysms.sms_freeAnalysis(analysis_params)
        pysms.sms_closeSF()
        pysms.sms_free()

        pd = simpl.SMSPeakDetection()
        pd.max_peaks = self.max_peaks
        pd.hop_size = self.hop_size 
        peaks = pd.find_peaks(audio)[0:self.num_frames]
        pt = simpl.SMSPartialTracking()
        pt.max_partials = self.max_peaks
        partials = pt.find_partials(peaks)

        # make sure both have the same number of partials
        assert len(sms_partials) == len(partials)

        # make sure each partial is the same
        for i in range(len(sms_partials)):
            assert sms_partials[i].get_length() == partials[i].get_length()
            for peak_number in range(sms_partials[i].get_length()):
                assert_almost_equals(sms_partials[i].peaks[peak_number].amplitude,
                                     partials[i].peaks[peak_number].amplitude,
                                     self.FLOAT_PRECISION)
                assert_almost_equals(sms_partials[i].peaks[peak_number].frequency,
                                     partials[i].peaks[peak_number].frequency,
                                     self.FLOAT_PRECISION)
                assert_almost_equals(sms_partials[i].peaks[peak_number].phase,
                                     partials[i].peaks[peak_number].phase,
                                     self.FLOAT_PRECISION)

    def test_sms_interpolate_frames(self):
        """test_sms_interpolate_frames
        Make sure that sms_interpolateFrames returns the expected values
        with interpolation factors of 0 and 1."""
        audio, sampling_rate = self.get_audio()
        pysms.sms_init()
        snd_header = pysms.SMS_SndHeader()
        # Try to open the input file to fill snd_header
        if(pysms.sms_openSF(self.input_file, snd_header)):
            raise NameError("error opening sound file: " + pysms.sms_errorString())
        analysis_params = self.pysms_analysis_params(sampling_rate)
        analysis_params.nFrames = self.num_frames
        if pysms.sms_initAnalysis(analysis_params, snd_header) != 0:
            raise Exception("Error allocating memory for analysis_params")
        analysis_params.iSizeSound = self.num_samples
        sms_header = pysms.SMS_Header()
        pysms.sms_fillHeader(sms_header, analysis_params, "pysms")

        interp_frame = pysms.SMS_Data()
        pysms.sms_allocFrameH(sms_header, interp_frame)

        sample_offset = 0
        size_new_data = 0
        current_frame = 0
        analysis_frames = []
        do_analysis = True

        while do_analysis and (current_frame < self.num_frames):
            sample_offset += size_new_data
            size_new_data = analysis_params.sizeNextRead
            frame = audio[sample_offset:sample_offset + size_new_data]
            # convert frame to floats for libsms
            frame = np.array(frame, dtype=np.float32)
            analysis_data = pysms.SMS_Data()
            pysms.sms_allocFrameH(sms_header, analysis_data)
            status = pysms.sms_analyze(frame, analysis_data, analysis_params)  

            if status == 1:
                analysis_frames.append(analysis_data)
                # test interpolateFrames on the last two analysis frames
                if current_frame == self.num_frames - 1:
                    left_frame = analysis_frames[-2]
                    right_frame = analysis_frames[-1]
                    pysms.sms_interpolateFrames(left_frame, right_frame, interp_frame, 0)
                    # make sure that interp_frame == left_frame
                    # interpolateFrames doesn't interpolate phases so ignore
                    left_amps = np.zeros(self.max_partials, dtype=np.float32)
                    left_freqs = np.zeros(self.max_partials, dtype=np.float32)
                    left_frame.getSinAmp(left_amps)
                    left_frame.getSinFreq(left_freqs)
                    right_amps = np.zeros(self.max_partials, dtype=np.float32)
                    right_freqs = np.zeros(self.max_partials, dtype=np.float32)
                    right_frame.getSinAmp(right_amps)
                    right_frame.getSinFreq(right_freqs)
                    interp_amps = np.zeros(self.max_partials, dtype=np.float32)
                    interp_freqs = np.zeros(self.max_partials, dtype=np.float32)
                    interp_frame.getSinAmp(interp_amps)
                    interp_frame.getSinFreq(interp_freqs)
                    for i in range(self.max_partials):
                        assert_almost_equals(left_amps[i], interp_amps[i],
                                             self.FLOAT_PRECISION)
                        if left_freqs[i] != 0:
                            assert_almost_equals(left_freqs[i], interp_freqs[i],
                                                 self.FLOAT_PRECISION)
                        else:
                            assert_almost_equals(right_freqs[i], interp_freqs[i],
                                                 self.FLOAT_PRECISION)
                    pysms.sms_interpolateFrames(left_frame, right_frame, interp_frame, 1)
                    interp_amps = np.zeros(self.max_partials, dtype=np.float32)
                    interp_freqs = np.zeros(self.max_partials, dtype=np.float32)
                    interp_frame.getSinAmp(interp_amps)
                    interp_frame.getSinFreq(interp_freqs)
                    for i in range(self.max_partials):
                        assert_almost_equals(right_amps[i], interp_amps[i],
                                             self.FLOAT_PRECISION)
                        if right_freqs[i] != 0:
                            assert_almost_equals(right_freqs[i], interp_freqs[i],
                                                 self.FLOAT_PRECISION)
                        else:
                            assert_almost_equals(left_freqs[i], interp_freqs[i],
                                                 self.FLOAT_PRECISION)
            elif status == -1:
                raise Exception("AnalysisStoppedEarly")
            else:
                pysms.sms_freeFrame(analysis_data)
            current_frame += 1

        for frame in analysis_frames:
            pysms.sms_freeFrame(frame)
        pysms.sms_freeFrame(interp_frame)
        pysms.sms_freeAnalysis(analysis_params)
        pysms.sms_closeSF()
        pysms.sms_free()

    def test_simplsms_interpolate_frames(self):
        """test_simplsms_interpolate_frames
        Make sure that sms_interpolateFrames returns the expected values
        with interpolation factors of 0 and 1."""
        audio, sampling_rate = self.get_audio()
        simplsms.sms_init()
        analysis_params = self.simplsms_analysis_params(sampling_rate)
        analysis_params.nFrames = self.num_frames
        if simplsms.sms_initAnalysis(analysis_params) != 0:
            raise Exception("Error allocating memory for analysis_params")
        analysis_params.iSizeSound = self.num_samples
        sms_header = simplsms.SMS_Header()
        simplsms.sms_fillHeader(sms_header, analysis_params, "simplsms")

        interp_frame = simplsms.SMS_Data()
        simplsms.sms_allocFrameH(sms_header, interp_frame)

        sample_offset = 0
        size_new_data = 0
        current_frame = 0
        analysis_frames = []
        do_analysis = True

        while do_analysis and (current_frame < self.num_frames):
            sample_offset += size_new_data
            size_new_data = analysis_params.sizeNextRead
            frame = audio[sample_offset:sample_offset + size_new_data]
            analysis_data = simplsms.SMS_Data()
            simplsms.sms_allocFrameH(sms_header, analysis_data)
            status = simplsms.sms_analyze(frame, analysis_data, analysis_params)  

            if status == 1:
                analysis_frames.append(analysis_data)
                # test interpolateFrames on the last two analysis frames
                if current_frame == self.num_frames - 1:
                    left_frame = analysis_frames[-2]
                    right_frame = analysis_frames[-1]
                    simplsms.sms_interpolateFrames(left_frame, right_frame, interp_frame, 0)
                    # make sure that interp_frame == left_frame
                    # interpolateFrames doesn't interpolate phases so ignore
                    left_amps = simpl.zeros(self.max_partials)
                    left_freqs = simpl.zeros(self.max_partials)
                    left_frame.getSinAmp(left_amps)
                    left_frame.getSinFreq(left_freqs)
                    right_amps = simpl.zeros(self.max_partials)
                    right_freqs = simpl.zeros(self.max_partials)
                    right_frame.getSinAmp(right_amps)
                    right_frame.getSinFreq(right_freqs)
                    interp_amps = simpl.zeros(self.max_partials)
                    interp_freqs = simpl.zeros(self.max_partials)
                    interp_frame.getSinAmp(interp_amps)
                    interp_frame.getSinFreq(interp_freqs)
                    for i in range(self.max_partials):
                        assert_almost_equals(left_amps[i], interp_amps[i],
                                             self.FLOAT_PRECISION)
                        if left_freqs[i] != 0:
                            assert_almost_equals(left_freqs[i], interp_freqs[i],
                                                 self.FLOAT_PRECISION)
                        else:
                            assert_almost_equals(right_freqs[i], interp_freqs[i],
                                                 self.FLOAT_PRECISION)
                    simplsms.sms_interpolateFrames(left_frame, right_frame, interp_frame, 1)
                    interp_amps = simpl.zeros(self.max_partials)
                    interp_freqs = simpl.zeros(self.max_partials)
                    interp_frame.getSinAmp(interp_amps)
                    interp_frame.getSinFreq(interp_freqs)
                    for i in range(self.max_partials):
                        assert_almost_equals(right_amps[i], interp_amps[i],
                                             self.FLOAT_PRECISION)
                        if right_freqs[i] != 0:
                            assert_almost_equals(right_freqs[i], interp_freqs[i],
                                                 self.FLOAT_PRECISION)
                        else:
                            assert_almost_equals(left_freqs[i], interp_freqs[i],
                                                 self.FLOAT_PRECISION)
            elif status == -1:
                raise Exception("AnalysisStoppedEarly")
            else:
                simplsms.sms_freeFrame(analysis_data)
            current_frame += 1

        for frame in analysis_frames:
            simplsms.sms_freeFrame(frame)
        simplsms.sms_freeFrame(interp_frame)
        simplsms.sms_freeAnalysis(analysis_params)
        simplsms.sms_free()

    def test_harmonic_synthesis(self):
        """test_harmonic_synthesis
        Compare pysms synthesised harmonic component with SMS synthesised 
        harmonic component."""
        audio, sampling_rate = self.get_audio()
        pysms.sms_init()
        snd_header = pysms.SMS_SndHeader()
        # Try to open the input file to fill snd_header
        if(pysms.sms_openSF(self.input_file, snd_header)):
            raise NameError("error opening sound file: " + pysms.sms_errorString())
        analysis_params = self.pysms_analysis_params(sampling_rate)
        analysis_params.nFrames = self.num_frames
        if pysms.sms_initAnalysis(analysis_params, snd_header) != 0:
            raise Exception("Error allocating memory for analysis_params")
        analysis_params.iSizeSound = self.num_samples
        sms_header = pysms.SMS_Header()
        pysms.sms_fillHeader(sms_header, analysis_params, "pysms")

        sample_offset = 0
        size_new_data = 0
        current_frame = 0
        analysis_frames = []
        do_analysis = True

        while do_analysis and (current_frame < self.num_frames):
            sample_offset += size_new_data
            size_new_data = analysis_params.sizeNextRead
            frame = audio[sample_offset:sample_offset + size_new_data]
            # convert frame to floats for libsms
            frame = np.array(frame, dtype=np.float32)
            analysis_data = pysms.SMS_Data()
            pysms.sms_allocFrameH(sms_header, analysis_data)
            status = pysms.sms_analyze(frame, analysis_data, analysis_params)  
            analysis_frames.append(analysis_data)
            if status == -1:
                do_analysis = False
            current_frame += 1

        synth_params = self.pysms_synthesis_params(sampling_rate)
        pysms.sms_initSynth(sms_header, synth_params)

        synth_samples = np.zeros(synth_params.sizeHop, dtype=np.float32)
        sms_audio = np.array([], dtype=np.float32)
        current_frame = 0

        while current_frame < len(analysis_frames):
            pysms.sms_synthesize(analysis_frames[current_frame], synth_samples, synth_params)
            sms_audio = np.hstack((sms_audio, synth_samples))
            current_frame += 1

        for frame in analysis_frames:
            pysms.sms_freeFrame(frame)
        pysms.sms_freeAnalysis(analysis_params)
        pysms.sms_closeSF()
        pysms.sms_freeSynth(synth_params)
        pysms.sms_free()

        pd = simpl.SMSPeakDetection()
        pd.max_peaks = self.max_peaks
        pd.hop_size = self.hop_size 
        pt = simpl.SMSPartialTracking()
        pt.max_partials = self.max_partials
        peaks = pd.find_peaks(audio)[0:self.num_frames]
        partials = pt.find_partials(peaks)
        synth = simpl.SMSSynthesis()
        synth.hop_size = self.hop_size
        synth.stochastic_type = pysms.SMS_STOC_NONE
        synth.synthesis_type = pysms.SMS_STYPE_DET
        synth.max_partials = self.max_partials
        simpl_audio = synth.synth(partials)

        assert len(sms_audio) == len(simpl_audio)
        for i in range(simpl_audio.size):
            assert_almost_equals(sms_audio[i], simpl_audio[i], self.FLOAT_PRECISION)

    #def test_residual_synthesis(self):
    #    """test_residual_synthesis
    #    Compare pysms residual signal with SMS residual""" 
    #    pysms.sms_init()
    #    sms_header = pysms.SMS_Header()
    #    snd_header = pysms.SMS_SndHeader()
    #    # Try to open the input file to fill snd_header
    #    if(pysms.sms_openSF(input_file, snd_header)):
    #        raise NameError("error opening sound file: " + pysms.sms_errorString())
    #    analysis_params = pysms.SMS_AnalParams()
    #    analysis_params.iSamplingRate = 44100
    #    analysis_params.iFrameRate = sampling_rate / hop_size
    #    sms_header.nStochasticCoeff = 128
    #    analysis_params.fDefaultFundamental = 100
    #    analysis_params.fHighestFreq = 20000
    #    analysis_params.iMaxDelayFrames = 3
    #    analysis_params.analDelay = 0
    #    analysis_params.minGoodFrames = 1
    #    analysis_params.iFormat = pysms.SMS_FORMAT_HP
    #    analysis_params.nTracks = max_partials
    #    analysis_params.nGuides = max_partials
    #    analysis_params.iWindowType = pysms.SMS_WIN_HAMMING
    #    pysms.sms_initAnalysis(analysis_params, snd_header)
    #    analysis_params.nFrames = num_samples / hop_size
    #    analysis_params.iSizeSound = num_samples
    #    analysis_params.peakParams.iMaxPeaks = max_peaks
    #    analysis_params.iStochasticType = pysms.SMS_STOC_APPROX
    #    pysms.sms_fillHeader(sms_header, analysis_params, "pysms")

    #    sample_offset = 0
    #    size_new_data = 0
    #    current_frame = 0
    #    sms_header.nFrames = num_frames
    #    analysis_frames = []
    #    do_analysis = True

    #    while do_analysis and (current_frame < num_frames-1):
    #        sample_offset += size_new_data
    #        if((sample_offset + analysis_params.sizeNextRead) < num_samples):
    #            size_new_data = analysis_params.sizeNextRead
    #        else:
    #            size_new_data = num_samples - sample_offset
    #        frame = audio[sample_offset:sample_offset + size_new_data]
    #        analysis_data = pysms.SMS_Data()
    #        pysms.sms_allocFrameH(sms_header, analysis_data)
    #        status = pysms.sms_analyze(frame, analysis_data, analysis_params)  
    #        analysis_frames.append(analysis_data)
    #        if status == -1:
    #            do_analysis = False
    #        current_frame += 1

    #    pysms.sms_freeAnalysis(analysis_params)
    #    pysms.sms_closeSF()
    #    pysms.sms_free()

    #    pd = simpl.SMSPeakDetection()
    #    pd.max_peaks = max_peaks
    #    pd.hop_size = hop_size
    #    pt = simpl.SMSPartialTracking()
    #    pt.max_partials = max_partials
    #    peaks = pd.find_peaks(audio)
    #    partials = pt.find_partials(peaks[0:num_frames])
    #    synth = simpl.SMSSynthesis()
    #    synth.hop_size = hop_size
    #    synth.stochastic_type = pysms.SMS_STOC_NONE
    #    synth.synthesis_type = pysms.SMS_STYPE_DET
    #    synth.max_partials = max_partials
    #    simpl_harmonic = synth.synth(partials)
    #    res = simpl.SMSResidual()
    #    res.num_coefficients = 128
    #    res.type = simpl.SMSResidual.TIME_DOMAIN
    #    residual = res.find_residual(simpl_harmonic, audio[0:simpl_harmonic.size])

if __name__ == "__main__":
    # run individual tests programatically
    # useful for debugging, particularly with GDB
    import nose
    argv = [__file__, 
            __file__ + ":TestSimplSMS.test_harmonic_synthesis"]
    nose.run(argv=argv)
